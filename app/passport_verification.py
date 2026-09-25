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
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.db import get_db
from app.models import AuditEvent, BorderEvent, PassportReview, PassportVerification, Person, TravelDocument
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


class PassportReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    outcome: Literal['consistent', 'inconsistent', 'inconclusive']
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class BorderEventRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    direction: Literal['entry', 'exit']
    port_code: ShortReference
    country_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=3)]
    occurred_at: datetime
    source_authority: ShortReference
    provenance_reference: AuditReference


class PassportReviewResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    verification_id: int
    reviewer_ref: str
    outcome: str
    reason: str
    source_comparison: str
    synthetic: bool
    correlation_id: str
    created_at: datetime


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
    review: PassportReviewResult | None
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
    db.flush()
    record_audit(
        db, event_type='passport_verification.created', entity_type='passport_verification',
        entity_id=record.id, actor_ref=operator, purpose='border_identity_verification',
        outcome=record.status, correlation_id=record.correlation_id,
    )
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


@router.post('/{verification_id}/border-event', status_code=201)
def create_border_event(
    verification_id: int, data: BorderEventRequest,
    operator: str = Depends(require_passport_operator), db: Session = Depends(get_db),
):
    record = db.get(PassportVerification, verification_id)
    if record is None or record.operator_ref != operator:
        raise HTTPException(404, 'Passport verification not found')
    if record.review_status != 'reviewed' or record.review is None or record.review.outcome != 'consistent':
        raise HTTPException(409, 'A consistent officer review is required before recording a border event')
    if record.status != 'completed' or record.comparison != 'match' or not record.passport_authenticated or not record.presentation_live:
        raise HTTPException(409, 'Passport evidence is not eligible for a border event')
    existing = db.scalar(select(BorderEvent).where(BorderEvent.passport_verification_id == record.id))
    if existing is not None:
        raise HTTPException(409, 'Passport verification already has a border event')
    event = BorderEvent(
        person_id=record.person_id, passport_verification_id=record.id,
        direction=data.direction, port_code=data.port_code, country_code=data.country_code,
        occurred_at=data.occurred_at, source_authority=data.source_authority,
        provenance_reference=data.provenance_reference,
    )
    db.add(event)
    try:
        db.flush()
        record_audit(
            db, event_type='border_event.created', entity_type='border_event',
            entity_id=event.id, actor_ref=operator, purpose='border_entry_exit_record',
            outcome=event.direction, correlation_id=record.correlation_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Passport verification already has a border event') from None
    db.refresh(event)
    return {
        'id': event.id, 'person_id': event.person_id,
        'passport_verification_id': event.passport_verification_id,
        'direction': event.direction, 'port_code': event.port_code,
        'country_code': event.country_code, 'occurred_at': event.occurred_at,
        'source_authority': event.source_authority,
        'provenance_reference': event.provenance_reference,
    }


@router.post('/{verification_id}/review', status_code=201, response_model=PassportReviewResult)
def review_verification(
    verification_id: int, data: PassportReviewRequest,
    operator: str = Depends(require_passport_operator), db: Session = Depends(get_db),
):
    record = db.get(PassportVerification, verification_id)
    if record is None or record.operator_ref != operator:
        raise HTTPException(404, 'Passport verification not found')
    if record.review_status != 'pending_officer_review':
        raise HTTPException(409, 'Passport verification already reviewed')

    if data.outcome != 'inconclusive':
        expected = 'match' if data.outcome == 'consistent' else 'no_match'
        if (record.status != 'completed' or record.comparison != expected
                or not record.passport_authenticated or not record.presentation_live):
            raise HTTPException(409, 'Available evidence does not support this outcome; further review required')

    review = PassportReview(
        verification_id=record.id, reviewer_ref=operator, outcome=data.outcome,
        reason=data.reason, source_comparison=record.comparison, synthetic=record.synthetic,
        correlation_id=record.correlation_id,
    )
    # Claim the pending state atomically so competing requests cannot both finalize it.
    state = 'reviewed' if data.outcome == 'consistent' else 'requires_follow_up'
    claimed = db.execute(
        update(PassportVerification)
        .where(PassportVerification.id == record.id,
               PassportVerification.operator_ref == operator,
               PassportVerification.review_status == 'pending_officer_review')
        .values(review_status=state)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Passport verification already reviewed')
    db.add(review)
    try:
        db.flush()
        record_audit(
            db, event_type='passport_review.created', entity_type='passport_verification',
            entity_id=record.id, actor_ref=operator, purpose='border_identity_verification',
            outcome=review.outcome, correlation_id=record.correlation_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Passport verification already reviewed') from None
    db.refresh(review)
    return review
