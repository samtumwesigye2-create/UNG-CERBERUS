import pytest

from app.biometrics import StubBiometricProvider, UnsupportedBiometricOperation
from app.models import BiometricReference, BiometricTransaction, BiometricCandidate, BiometricDisposition, Person


def test_biometric_metadata_supports_approved_modalities_without_person_raw_capture():
    assert {'fingerprint', 'face', 'iris'} == StubBiometricProvider.supported_modalities
    assert not hasattr(Person, 'raw_biometric')
    assert not hasattr(Person, 'biometric_template')
    assert BiometricReference.__tablename__ == 'biometric_references'
    assert BiometricTransaction.__tablename__ == 'biometric_transactions'
    assert BiometricCandidate.__tablename__ == 'biometric_candidates'
    assert BiometricDisposition.__tablename__ == 'biometric_dispositions'


def test_provider_capability_failure_is_explicit():
    provider = StubBiometricProvider(supported_operations={'enroll', 'verify'})
    with pytest.raises(UnsupportedBiometricOperation):
        provider.identify(modality='face', sample_reference='synthetic-sample', authorization_reference='AUTH-1')
