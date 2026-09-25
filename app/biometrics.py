from typing import Protocol


class UnsupportedBiometricOperation(RuntimeError):
    pass


class BiometricProvider(Protocol):
    def enroll(self, *, modality: str, sample_reference: str) -> dict: ...
    def verify(self, *, modality: str, sample_reference: str, provider_reference: str) -> dict: ...
    def identify(self, *, modality: str, sample_reference: str) -> list[dict]: ...


class StubBiometricProvider:
    """Deterministic synthetic provider used for tests and local development only."""

    supported_modalities = {'fingerprint', 'face', 'iris'}

    def __init__(self, capabilities=None):
        self.capabilities = set(capabilities or {'enroll', 'verify', 'identify'})

    def _require(self, operation: str, modality: str):
        if operation not in self.capabilities:
            raise UnsupportedBiometricOperation(f'{operation} is not supported')
        if modality not in self.supported_modalities:
            raise UnsupportedBiometricOperation(f'unsupported modality: {modality}')

    def enroll(self, *, modality: str, sample_reference: str) -> dict:
        self._require('enroll', modality)
        return {'provider_reference': f'stub://{modality}/{abs(hash(sample_reference))}', 'status': 'enrolled'}

    def verify(self, *, modality: str, sample_reference: str, provider_reference: str) -> dict:
        self._require('verify', modality)
        return {'status': 'candidate_match', 'score': 1.0 if sample_reference else 0.0, 'provider_reference': provider_reference}

    def identify(self, *, modality: str, sample_reference: str) -> list[dict]:
        self._require('identify', modality)
        return []
