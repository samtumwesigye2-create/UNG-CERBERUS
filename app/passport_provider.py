"""One presented passport and one presented traveler; no enrollment/search API.

Real adapters must authenticate the passport chip, bind fresh reader/capture
sessions to this document and operator/device, and check presentation liveness.
The application never downloads client-supplied references as URLs.
"""
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict


class PassportEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    document_number: str
    issuing_jurisdiction: str
    passport_authenticated: bool
    presentation_live: bool
    comparison: Literal['match', 'no_match', 'inconclusive']


class PassportProvider(Protocol):
    name: str
    synthetic: bool

    def verify_presented_passport(
        self, *, modality: str, document_number: str, issuing_jurisdiction: str,
        passport_session_reference: str, traveler_sample_reference: str,
        operator_ref: str, device_reference: str,
    ) -> PassportEvidence: ...


class UnavailablePassportProvider:
    name = 'unconfigured'
    synthetic = False

    def verify_presented_passport(self, **kwargs) -> PassportEvidence:
        raise ConnectionError('No trusted passport provider configured')


class SyntheticPassportProvider:
    """Explicit demo fixtures, not a biometric algorithm or document authenticator."""
    name = 'synthetic-passport-demo'
    synthetic = True

    def verify_presented_passport(
        self, *, modality, document_number, issuing_jurisdiction,
        passport_session_reference, traveler_sample_reference,
        operator_ref, device_reference,
    ) -> PassportEvidence:
        authenticated = (
            document_number == 'SYNTH-PASSPORT-001'
            and issuing_jurisdiction == 'TEST'
            and passport_session_reference == f'synthetic://passport/{modality}/demo-001'
        )
        matching = f'synthetic://traveler/{modality}/demo-001'
        different = f'synthetic://traveler/{modality}/demo-other'
        live = traveler_sample_reference in {matching, different}
        comparison = 'inconclusive'
        if authenticated and live:
            comparison = 'match' if traveler_sample_reference == matching else 'no_match'
        return PassportEvidence(
            document_number=document_number, issuing_jurisdiction=issuing_jurisdiction,
            passport_authenticated=authenticated, presentation_live=live, comparison=comparison,
        )
