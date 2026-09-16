"""Authenticated, passport-only 1:1 result workflow."""
import os
from datetime import date, datetime
from secrets import compare_digest
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PassportVerification, Person, TravelDocument
from app.passport_provider import (
    PassportEvidence, PassportProvider, SyntheticPassportProvider, UnavailablePassportProvider,
)


class RedactedValidationRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def redacted_handler(request: Request):
            try:
                return await handler(request)
            except RequestValidationError:
                # Pydantic's default error contains input values, potentially raw samples.
                return JSONResponse(status_code=422, content={'detail': 'Invalid passport verification request'})
        return redacted_handler


router = APIRouter(prefix='/v1/passport-verifications', tags=['Passport verification'], route_class=RedactedValidationRoute)
bearer = HTTPBearer(auto_error=False)
ShortReference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
AuditReference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
SessionReference = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]


class PassportVerificationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    person_id: int = Field(gt=0)
    document_id: int = Field(gt=0)
    modality: Literal['face', 'fingerprint', 'iris'] = 'face'
    passport_session_reference: SessionReference
    traveler_sample_reference: SessionReference
    device_reference: ShortReference
    authorization_reference: AuditReference
    provenance_reference: AuditReference


class PassportVerificationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    person_id: int
    document_id: int
    modality: str
    provider: str
    synthetic: bool
    operator_ref: str
    device_reference: str
    purpose: str
    authorization_reference: str
    provenance_reference: str
    status: str
    comparison: str
    passport_authenticated: bool | None
    presentation_live: bool | None
    review_status: str
    correlation_id: str
    created_at: datetime


def require_passport_operator(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    token = os.getenv('CERBERUS_PASSPORT_TOKEN', '')
    operator = os.getenv('CERBERUS_PASSPORT_OPERATOR', '').strip()
    if len(token) < 32 or not operator or len(operator) > 120:
        raise HTTPException(503, 'Passport officer authentication is not configured')
    if credentials is None or not compare_digest(credentials.credentials.encode(), token.encode()):
        raise HTTPException(401, 'Officer authentication required', headers={'WWW-Authenticate': 'Bearer'})
    return operator


def get_passport_provider() -> PassportProvider:
    # Synthetic mode requires explicit server configuration, never a request field.
    if os.getenv('CERBERUS_PASSPORT_PROVIDER') == 'synthetic':
        return SyntheticPassportProvider()
    return UnavailablePassportProvider()


@router.post('', status_code=201, response_model=PassportVerificationResult)
def verify_passport(
    data: PassportVerificationRequest, response: Response,
    operator: str = Depends(require_passport_operator), db: Session = Depends(get_db),
    provider: PassportProvider = Depends(get_passport_provider),
):
    document = db.get(TravelDocument, data.document_id)
    person = db.get(Person, data.person_id)
    if document is None or person is None or document.person_id != data.person_id:
        raise HTTPException(404, 'Passport for this traveler not found')
    if (person.status != 'active' or document.document_type != 'passport'
            or document.status != 'active' or document.expires_on is None
            or document.expires_on < date.today()
            or (document.issued_on is not None and document.issued_on > date.today())):
        raise HTTPException(409, 'Active, currently valid passport and traveler record required')

    record = PassportVerification(
        person_id=data.person_id, document_id=data.document_id, modality=data.modality,
        provider=provider.name, synthetic=provider.synthetic, operator_ref=operator,
        device_reference=data.device_reference, authorization_reference=data.authorization_reference,
        provenance_reference=data.provenance_reference, correlation_id=str(uuid4()),
        status='completed', comparison='inconclusive',
    )
    try:
        result = provider.verify_presented_passport(
            modality=data.modality, document_number=document.document_number,
            issuing_jurisdiction=document.issuing_jurisdiction,
            passport_session_reference=data.passport_session_reference,
            traveler_sample_reference=data.traveler_sample_reference,
            operator_ref=operator, device_reference=data.device_reference,
        )
        # Revalidate provider output; do not trust a dict's truthy strings or extra payloads.
        evidence = PassportEvidence.model_validate(
            result.model_dump() if isinstance(result, PassportEvidence) else result
        )
        record.passport_authenticated = (
            evidence.passport_authenticated
            and evidence.document_number == document.document_number
            and evidence.issuing_jurisdiction == document.issuing_jurisdiction
        )
        record.presentation_live = evidence.presentation_live
        if record.passport_authenticated and record.presentation_live:
            record.comparison = evidence.comparison
    except (TimeoutError, ConnectionError):
        record.status = 'provider_unavailable'
        response.status_code = 503
    except Exception:
        # Store a safe failure code, never provider exceptions or capture references.
        record.status = 'failed'
        response.status_code = 502
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get('/{verification_id}', response_model=PassportVerificationResult)
def get_verification(
    verification_id: int, operator: str = Depends(require_passport_operator),
    db: Session = Depends(get_db),
):
    record = db.get(PassportVerification, verification_id)
    if record is None or record.operator_ref != operator:
        raise HTTPException(404, 'Passport verification not found')
    return record
