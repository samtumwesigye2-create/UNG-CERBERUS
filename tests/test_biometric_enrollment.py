from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_governed_biometric_enrollment_hides_raw_sample():
    with client:
        person = client.post('/v1/people', json={
            'primary_name': 'Synthetic Biometric Person',
            'source_authority': 'TEST-AUTHORITY',
            'provenance_reference': 'SYNTH-PERSON-001'
        }).json()
        response = client.post('/v1/biometrics/enrollments', json={
            'person_id': person['id'],
            'modality': 'fingerprint',
            'provider': 'stub',
            'sample_reference': 'synthetic://fingerprint/sample-001',
            'operator_ref': 'operator-test-01',
            'device_reference': 'device-test-01',
            'purpose': 'identity_enrollment',
            'authorization_reference': 'AUTH-SYNTH-001',
            'provenance_reference': 'BIO-SYNTH-001'
        })
        assert response.status_code == 201
        body = response.json()
        assert body['modality'] == 'fingerprint'
        assert body['provider'] == 'stub'
        assert body['provider_reference'].startswith('stub://fingerprint/')
        assert body['status'] == 'active'
        assert 'sample_reference' not in body
        assert 'raw_sample' not in body
        fetched = client.get(f"/v1/people/{person['id']}").json()
        assert 'sample_reference' not in fetched
        assert 'biometric' not in fetched


def test_biometric_enrollment_requires_governance_metadata():
    with client:
        person = client.post('/v1/people', json={
            'primary_name': 'Synthetic Missing Authority',
            'source_authority': 'TEST-AUTHORITY'
        }).json()
        response = client.post('/v1/biometrics/enrollments', json={
            'person_id': person['id'],
            'modality': 'fingerprint',
            'provider': 'stub',
            'sample_reference': 'synthetic://fingerprint/sample-002',
            'operator_ref': 'operator-test-02',
            'device_reference': 'device-test-02',
            'purpose': '',
            'authorization_reference': '',
            'provenance_reference': 'BIO-SYNTH-002'
        })
        assert response.status_code == 422


def test_biometric_enrollment_rejects_unsupported_modality_and_unknown_person():
    with client:
        person = client.post('/v1/people', json={
            'primary_name': 'Synthetic Modality Person',
            'source_authority': 'TEST-AUTHORITY'
        }).json()
        payload = {
            'person_id': person['id'], 'modality': 'voice', 'provider': 'stub',
            'sample_reference': 'synthetic://voice/sample-001',
            'operator_ref': 'operator-test-03', 'device_reference': 'device-test-03',
            'purpose': 'identity_enrollment', 'authorization_reference': 'AUTH-SYNTH-003',
            'provenance_reference': 'BIO-SYNTH-003'
        }
        assert client.post('/v1/biometrics/enrollments', json=payload).status_code == 422
        payload['modality'] = 'face'
        payload['person_id'] = 99999999
        assert client.post('/v1/biometrics/enrollments', json=payload).status_code == 404
