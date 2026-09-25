from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_identity_document_and_case_workflow():
    person = client.post('/v1/people', json={
        'primary_name': 'Amina N.',
        'date_of_birth': '1990-01-02',
        'nationality': 'UG',
        'citizenship': 'UG',
        'source_authority': 'IMMIGRATION',
        'provenance_reference': 'ENROLL-001',
        'aliases': ['Amina Nakato']
    }).json()
    assert person['person_code'].startswith('CER-P-')
    assert person['aliases'] == ['Amina Nakato']

    fetched = client.get(f"/v1/people/{person['id']}")
    assert fetched.status_code == 200
    assert fetched.json()['id'] == person['id']

    doc = client.post(f"/v1/people/{person['id']}/documents", json={
        'document_type': 'passport',
        'document_number': 'UG1234567',
        'issuing_jurisdiction': 'UG',
        'issued_on': '2025-01-01',
        'expires_on': '2035-01-01',
        'status': 'active',
        'verification_provenance': 'DOC-CHECK-001'
    })
    assert doc.status_code == 201
    assert doc.json()['person_id'] == person['id']

    case = client.post('/v1/cases', json={
        'person_id': person['id'],
        'case_type': 'entry_review',
        'jurisdiction': 'UG',
        'assigned_unit': 'PORT-OPS'
    })
    assert case.status_code == 201
    case_id = case.json()['id']
    assert case.json()['status'] == 'open'

    transition = client.post(f'/v1/cases/{case_id}/transitions', json={
        'status': 'under_review',
        'actor_ref': 'officer-1',
        'reason': 'Document review'
    })
    assert transition.status_code == 200
    assert transition.json()['status'] == 'under_review'
    assert transition.json()['history'][-1]['actor_ref'] == 'officer-1'
