import pytest


def test_biometric_gateway_supports_governed_modalities_without_raw_person_data():
    from app.biometrics import StubBiometricProvider, UnsupportedBiometricOperation
    from app.models import Person, BiometricReference, BiometricTransaction, BiometricCandidate, BiometricDisposition

    assert {'fingerprint', 'face', 'iris'} == StubBiometricProvider.supported_modalities
    assert not hasattr(Person, 'raw_biometric')
    assert not hasattr(Person, 'biometric_template')

    for model in (BiometricReference, BiometricTransaction, BiometricCandidate, BiometricDisposition):
        assert hasattr(model, '__tablename__')

    provider = StubBiometricProvider(capabilities={'enroll', 'verify'})
    with pytest.raises(UnsupportedBiometricOperation):
        provider.identify(modality='face', sample_reference='synthetic://sample/1')
