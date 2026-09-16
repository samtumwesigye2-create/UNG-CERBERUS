from dataclasses import dataclass


class UnsupportedBiometricOperation(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderResult:
    status: str
    provider_reference: str | None = None
    score: float | None = None
    candidates: tuple[dict, ...] = ()


class StubBiometricProvider:
    """Deterministic synthetic provider used for tests and local development only."""

    supported_modalities = {'fingerprint', 'face', 'iris'}

    def __init__(self, supported_operations=None):
        self.supported_operations = supported_operations or {'enroll', 'verify', 'identify'}

    def _require(self, operation: str, modality: str):
        if operation not in self.supported_operations:
            raise UnsupportedBiometricOperation(operation)
        if modality not in self.supported_modalities:
            raise UnsupportedBiometricOperation(modality)

    def enroll(self, *, modality: str, sample_reference: str, authorization_reference: str):
        self._require('enroll', modality)
        return ProviderResult(status='completed', provider_reference=f'stub:{modality}:{sample_reference}')

    def verify(self, *, modality: str, sample_reference: str, provider_reference: str, authorization_reference: str):
        self._require('verify', modality)
        return ProviderResult(status='completed', provider_reference=provider_reference, score=1.0)

    def identify(self, *, modality: str, sample_reference: str, authorization_reference: str):
        self._require('identify', modality)
        return ProviderResult(status='completed', candidates=())
