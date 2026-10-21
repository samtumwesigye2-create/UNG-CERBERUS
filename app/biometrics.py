


class UnsupportedBiometricOperation(RuntimeError):
    pass




class StubBiometricProvider:
    """Deterministic synthetic provider used for tests and local development only."""

    supported_modalities = {'fingerprint', 'face', 'iris'}

