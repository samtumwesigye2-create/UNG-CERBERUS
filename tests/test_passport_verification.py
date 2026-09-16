"""Passport checks are 1:1 and must never create enrollment or screening state."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import BiometricReference, BiometricCandidate, ScreeningEvent, TravelDocument

TOKEN = 'test-only-officer-token-0000000000000000'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}
URL = '/v1/passport-verifications'


@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv('CERBERUS_PASSPORT_TOKEN', TOKEN)
    monkeypatch.setenv('CERBERUS_PASSPORT_OPERATOR', 'synthetic-officer')
    monkeypatch.setenv('CERBERUS_PASSPORT_PROVIDER', 'synthetic')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    with TestClient(app) as client:
        person = client.post('/v1/people', json={
            'primary_name': 'Synthetic Traveler', 'source_authority': 'TEST'
        }).json()
        document = client.post(f"/v1/people/{person['id']}/documents", json={
            'document_type': 'passport', 'document_number': 'SYNTH-PASSPORT-001',
            'issuing_jurisdiction': 'TEST',
            'expires_on': (date.today() + timedelta(days=365)).isoformat()
        }).json()
        payload = {
            'person_id': person['id'], 'document_id': document['id'], 'modality': 'face',
            'passport_session_reference': 'synthetic://passport/face/demo-001',
            'traveler_sample_reference': 'synthetic://traveler/face/demo-001',
            'device_reference': 'synthetic-reader', 'authorization_reference': 'TEST-AUTH',
            'provenance_reference': 'TEST-CHECK'
        }
        yield client, engine, payload
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.parametrize('modality', ['face', 'fingerprint', 'iris'])
def test_verification_records_metadata_only_without_enrolling_or_screening(context, modality):
    client, engine, payload = context
    payload.update(modality=modality,
                   passport_session_reference=f'synthetic://passport/{modality}/demo-001',
                   traveler_sample_reference=f'synthetic://traveler/{modality}/demo-001')
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body['comparison'] == 'match'
    assert body['status'] == 'completed'
    assert body['review_status'] == 'pending_officer_review'
    assert body['synthetic'] is True
    assert body['operator_ref'] == 'synthetic-officer'
    assert body['document_id'] == payload['document_id']
    assert body['passport_authenticated'] is True
    assert body['presentation_live'] is True
    assert client.get(f"{URL}/{body['id']}", headers=HEADERS).json() == body
    person = client.get(f"/v1/people/{payload['person_id']}").json()
    assert 'biometric' not in person
    with Session(engine) as db:
        for model in (BiometricReference, BiometricCandidate, ScreeningEvent):
            assert db.scalar(select(func.count()).select_from(model)) == 0
    with engine.connect() as conn:
        dump = '\n'.join(conn.connection.driver_connection.iterdump())
    for sensitive in ('synthetic://passport/', 'synthetic://traveler/', TOKEN):
        assert sensitive not in dump
        assert sensitive not in response.text


def test_nonmatching_traveler_does_not_become_a_match(context):
    client, _, payload = context
    payload['traveler_sample_reference'] = 'synthetic://traveler/face/demo-other'
    body = client.post(URL, headers=HEADERS, json=payload).json()
    assert body['comparison'] == 'no_match'
    assert body['review_status'] == 'pending_officer_review'


@pytest.mark.parametrize('headers', [{}, {'Authorization': 'Bearer wrong'}])
def test_missing_or_wrong_officer_credentials_cannot_write_or_read(context, headers):
    client, _, payload = context
    assert client.post(URL, headers=headers, json=payload).status_code == 401
    assert client.get(f'{URL}/1', headers=headers).status_code == 401


def test_missing_server_credentials_fail_closed(context, monkeypatch):
    client, _, payload = context
    monkeypatch.delenv('CERBERUS_PASSPORT_TOKEN')
    assert client.post(URL, headers=HEADERS, json=payload).status_code == 503


@pytest.mark.parametrize('field,value', [
    ('authorization_reference', '  '), ('provenance_reference', ''),
    ('device_reference', ''), ('modality', 'voice'), ('person_id', 0),
    ('passport_session_reference', ''), ('traveler_sample_reference', ''),
    ('provider', 'synthetic'), ('operator_ref', 'spoofed-officer'),
    ('raw_sample', 'SECRET-RAW-PAYLOAD'), ('candidate_person_ids', [1, 2]),
])
def test_invalid_input_and_client_overrides_are_rejected_without_echoing_handles(context, field, value):
    client, _, payload = context
    payload[field] = value
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 422
    assert 'synthetic://' not in response.text
    assert 'SECRET-RAW-PAYLOAD' not in response.text


@pytest.mark.parametrize('change', ['other_person', 'expired', 'inactive', 'not_passport', 'missing_expiry', 'unknown'])
def test_only_active_presented_passport_for_claimed_person_is_accepted(context, change):
    client, engine, payload = context
    with Session(engine) as db:
        doc = db.get(TravelDocument, payload['document_id'])
        if change == 'other_person':
            other = client.post('/v1/people', json={'primary_name': 'Other', 'source_authority': 'TEST'}).json()
            payload['person_id'] = other['id']
        elif change == 'expired': doc.expires_on = date.today() - timedelta(days=1)
        elif change == 'inactive': doc.status = 'revoked'
        elif change == 'not_passport': doc.document_type = 'national_id'
        elif change == 'missing_expiry': doc.expires_on = None
        elif change == 'unknown': payload['document_id'] = 999999
        db.commit()
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == (404 if change in {'unknown', 'other_person'} else 409)


def test_provider_checks_passport_session_binding(context):
    client, _, payload = context
    payload['passport_session_reference'] = 'synthetic://passport/face/untrusted'
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body['comparison'] == 'inconclusive'
    assert body['passport_authenticated'] is False
    assert body['review_status'] == 'pending_officer_review'


def test_no_configured_provider_records_unavailable_without_guessing(context, monkeypatch):
    client, _, payload = context
    monkeypatch.delenv('CERBERUS_PASSPORT_PROVIDER')
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 503
    body = response.json()
    assert body['status'] == 'provider_unavailable'
    assert body['comparison'] == 'inconclusive'
    assert body['synthetic'] is False
    assert body['passport_authenticated'] is None
    assert client.get(f"{URL}/{body['id']}", headers=HEADERS).json() == body


def test_officer_cannot_read_another_officers_record(context, monkeypatch):
    client, _, payload = context
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 201
    monkeypatch.setenv('CERBERUS_PASSPORT_OPERATOR', 'other-officer')
    assert client.get(f"{URL}/{response.json()['id']}", headers=HEADERS).status_code == 404


@pytest.mark.parametrize('failure,expected_status,expected_http', [
    (TimeoutError, 'provider_unavailable', 503),
    (ConnectionError, 'provider_unavailable', 503),
    (RuntimeError, 'failed', 502),
])
def test_provider_failures_are_persisted_without_sensitive_exception_text(context, failure, expected_status, expected_http):
    from app.passport_verification import get_passport_provider
    client, engine, payload = context
    class BrokenReader:
        name = 'test-reader'
        synthetic = True
        def verify_presented_passport(self, **kwargs):
            raise failure('SECRET-PROVIDER-CREDENTIAL synthetic://private-capture')
    app.dependency_overrides[get_passport_provider] = BrokenReader
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == expected_http
    body = response.json()
    assert body['status'] == expected_status
    assert body['comparison'] == 'inconclusive'
    assert body['passport_authenticated'] is None
    assert client.get(f"{URL}/{body['id']}", headers=HEADERS).json() == body
    with engine.connect() as conn:
        dump = '\n'.join(conn.connection.driver_connection.iterdump())
    assert 'SECRET-PROVIDER-CREDENTIAL' not in dump + response.text
    assert 'private-capture' not in dump + response.text


@pytest.mark.parametrize('field,value', [
    ('document_number', 'ANOTHER-PASSPORT'), ('issuing_jurisdiction', 'OTHER'),
    ('passport_authenticated', False), ('presentation_live', False),
])
def test_match_is_inconclusive_without_document_binding_and_live_presentation(context, field, value):
    from app.passport_verification import get_passport_provider
    client, _, payload = context
    class UntrustedEvidenceReader:
        name = 'test-reader'
        synthetic = True
        def verify_presented_passport(self, **kwargs):
            result = {'document_number': 'SYNTH-PASSPORT-001', 'issuing_jurisdiction': 'TEST',
                      'passport_authenticated': True, 'presentation_live': True, 'comparison': 'match'}
            result[field] = value
            return result
    app.dependency_overrides[get_passport_provider] = UntrustedEvidenceReader
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 201
    assert response.json()['comparison'] == 'inconclusive'
    assert response.json()['review_status'] == 'pending_officer_review'


def test_malformed_provider_evidence_cannot_become_a_match(context):
    from app.passport_verification import get_passport_provider
    client, _, payload = context
    class MalformedReader:
        name = 'test-reader'
        synthetic = True
        def verify_presented_passport(self, **kwargs):
            return {'document_number': 'SYNTH-PASSPORT-001', 'issuing_jurisdiction': 'TEST',
                    'passport_authenticated': 'false', 'presentation_live': True, 'comparison': 'match'}
    app.dependency_overrides[get_passport_provider] = MalformedReader
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 502
    assert response.json()['status'] == 'failed'
    assert response.json()['comparison'] == 'inconclusive'


def test_document_from_different_passport_is_not_accepted_by_synthetic_reader(context):
    client, engine, payload = context
    with Session(engine) as db:
        document = db.get(TravelDocument, payload['document_id'])
        document.document_number = 'ANOTHER-PASSPORT'
        db.commit()
    response = client.post(URL, headers=HEADERS, json=payload)
    assert response.status_code == 201
    assert response.json()['passport_authenticated'] is False
    assert response.json()['comparison'] == 'inconclusive'


def test_officer_review_records_reason_and_preserves_original_evidence(context):
    client, engine, payload = context
    original = client.post(URL, headers=HEADERS, json=payload).json()
    review_url = f"{URL}/{original['id']}/review"
    response = client.post(review_url, headers=HEADERS, json={
        'outcome': 'consistent', 'reason': 'Presented passport evidence reviewed.'
    })
    assert response.status_code == 201
    review = response.json()
    assert review['reviewer_ref'] == 'synthetic-officer'
    assert review['outcome'] == 'consistent'
    assert review['reason'] == 'Presented passport evidence reviewed.'
    assert review['synthetic'] is True
    assert review['correlation_id'] == original['correlation_id']
    assert review['verification_id'] == original['id']
    assert review['source_comparison'] == 'match'
    after = client.get(f"{URL}/{original['id']}", headers=HEADERS).json()
    assert after['review_status'] == 'reviewed'
    assert after['review'] == review
    for key in ('comparison', 'status', 'passport_authenticated', 'presentation_live', 'synthetic'):
        assert after[key] == original[key]
    assert client.post(review_url, headers=HEADERS, json={
        'outcome': 'inconclusive', 'reason': 'Trying to overwrite the first review.'
    }).status_code == 409
    assert client.get(f"{URL}/{original['id']}", headers=HEADERS).json()['review'] == review
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ScreeningEvent)) == 0


@pytest.mark.parametrize('source,outcome,expected', [
    ('match', 'inconsistent', 409), ('no_match', 'consistent', 409),
    ('unavailable', 'consistent', 409), ('unavailable', 'inconsistent', 409),
    ('untrusted', 'consistent', 409), ('untrusted', 'inconsistent', 409),
    ('no_match', 'inconsistent', 201), ('unavailable', 'inconclusive', 201),
    ('untrusted', 'inconclusive', 201), ('match', 'inconclusive', 201),
])
def test_review_cannot_promote_missing_or_contradictory_evidence(context, monkeypatch, source, outcome, expected):
    client, _, payload = context
    if source == 'no_match': payload['traveler_sample_reference'] = 'synthetic://traveler/face/demo-other'
    elif source == 'unavailable': monkeypatch.delenv('CERBERUS_PASSPORT_PROVIDER')
    elif source == 'untrusted': payload['passport_session_reference'] = 'synthetic://untrusted'
    original = client.post(URL, headers=HEADERS, json=payload).json()
    response = client.post(f"{URL}/{original['id']}/review", headers=HEADERS, json={
        'outcome': outcome, 'reason': 'Officer inspected available evidence.'
    })
    assert response.status_code == expected
    after = client.get(f"{URL}/{original['id']}", headers=HEADERS).json()
    assert after['comparison'] == original['comparison']
    assert after['status'] == original['status']
    if expected == 409:
        assert after['review_status'] == 'pending_officer_review'
        assert after['review'] is None
    elif outcome != 'consistent':
        assert after['review_status'] == 'requires_follow_up'


@pytest.mark.parametrize('body', [
    {'outcome': 'consistent'},
    {'outcome': 'consistent', 'reason': '   '},
    {'outcome': 'consistent', 'reason': 'x' * 1001},
    {'outcome': 'admit_traveler', 'reason': 'Not an immigration decision endpoint'},
    {'outcome': 'consistent', 'reason': 'Reviewed', 'reviewer_ref': 'spoofed'},
])
def test_officer_review_validates_reason_and_rejects_actor_spoofing(context, body):
    client, _, payload = context
    original = client.post(URL, headers=HEADERS, json=payload).json()
    response = client.post(f"{URL}/{original['id']}/review", headers=HEADERS, json=body)
    assert response.status_code == 422
    assert client.get(f"{URL}/{original['id']}", headers=HEADERS).json()['review_status'] == 'pending_officer_review'


def test_officer_review_requires_authorized_owner(context, monkeypatch):
    client, _, payload = context
    original = client.post(URL, headers=HEADERS, json=payload).json()
    review_url = f"{URL}/{original['id']}/review"
    body = {'outcome': 'consistent', 'reason': 'Reviewed'}
    assert client.post(review_url, json=body).status_code == 401
    monkeypatch.setenv('CERBERUS_PASSPORT_OPERATOR', 'other-officer')
    assert client.post(review_url, headers=HEADERS, json=body).status_code == 404
    assert client.post(f'{URL}/999999/review', headers=HEADERS, json=body).status_code == 404


def _reviewed_passport(context, *, outcome='consistent'):
    client, engine, payload = context
    original = client.post(URL, headers=HEADERS, json=payload).json()
    review = client.post(f"{URL}/{original['id']}/review", headers=HEADERS, json={
        'outcome': outcome, 'reason': 'Border officer reviewed passport evidence.'
    })
    return client, engine, payload, original, review


def test_reviewed_passport_creates_one_governed_entry_event(context):
    client, _, payload, original, review = _reviewed_passport(context)
    assert review.status_code == 201
    response = client.post(f"{URL}/{original['id']}/border-event", headers=HEADERS, json={
        'direction': 'entry', 'port_code': 'EBB', 'country_code': 'UG',
        'occurred_at': '2026-09-16T10:00:00Z', 'source_authority': 'IMMIGRATION',
        'provenance_reference': 'BORDER-CHECK-001',
    })
    assert response.status_code == 201
    body = response.json()
    assert body['direction'] == 'entry'
    assert body['port_code'] == 'EBB'
    assert body['person_id'] == payload['person_id']
    assert body['passport_verification_id'] == original['id']


def test_reviewed_passport_creates_exit_event_and_cannot_be_reused(context):
    client, _, _, original, review = _reviewed_passport(context)
    assert review.status_code == 201
    body = {
        'direction': 'exit', 'port_code': 'EBB', 'country_code': 'UG',
        'occurred_at': '2026-09-16T11:00:00Z', 'source_authority': 'IMMIGRATION',
        'provenance_reference': 'BORDER-CHECK-002',
    }
    assert client.post(f"{URL}/{original['id']}/border-event", headers=HEADERS, json=body).status_code == 201
    assert client.post(f"{URL}/{original['id']}/border-event", headers=HEADERS, json=body).status_code == 409


@pytest.mark.parametrize('outcome', ['inconclusive', 'inconsistent'])
def test_border_event_requires_consistent_officer_review(context, outcome):
    client, _, _, original, review = _reviewed_passport(context, outcome=outcome)
    assert review.status_code == (201 if outcome == 'inconclusive' else 409)
    if outcome == 'inconclusive':
        response = client.post(f"{URL}/{original['id']}/border-event", headers=HEADERS, json={
            'direction': 'entry', 'port_code': 'EBB', 'country_code': 'UG',
            'occurred_at': '2026-09-16T12:00:00Z', 'source_authority': 'IMMIGRATION',
            'provenance_reference': 'BORDER-CHECK-003',
        })
        assert response.status_code == 409


def test_border_event_rejects_unreviewed_passport_and_actor_spoofing(context):
    client, _, _, original, _ = _reviewed_passport(context)
    # Create a second pending check and verify it cannot produce an event.
    pending = client.post(URL, headers=HEADERS, json={
        **context[2], 'provenance_reference': 'PENDING-CHECK',
    }).json()
    body = {
        'direction': 'entry', 'port_code': 'EBB', 'country_code': 'UG',
        'occurred_at': '2026-09-16T13:00:00Z', 'source_authority': 'IMMIGRATION',
        'provenance_reference': 'BORDER-CHECK-004',
    }
    assert client.post(f"{URL}/{pending['id']}/border-event", headers=HEADERS, json=body).status_code == 409
    assert client.post(f"{URL}/{original['id']}/border-event", json=body).status_code == 401


def test_border_event_does_not_change_passport_review_or_make_an_admission_decision(context):
    client, _, _, original, _ = _reviewed_passport(context)
    body = {
        'direction': 'entry', 'port_code': 'EBB', 'country_code': 'UG',
        'occurred_at': '2026-09-16T14:00:00Z', 'source_authority': 'IMMIGRATION',
        'provenance_reference': 'BORDER-CHECK-005',
    }
    assert client.post(f"{URL}/{original['id']}/border-event", headers=HEADERS, json=body).status_code == 201
    result = client.get(f"{URL}/{original['id']}", headers=HEADERS).json()
    assert result['review_status'] == 'reviewed'
    assert result['review']['outcome'] == 'consistent'
    assert 'admission_decision' not in result
    assert 'denial_decision' not in result


def test_legacy_border_event_route_is_retired(context):
    client, _, payload = context
    response = client.post('/v1/border-events', json={
        'person_id': payload['person_id'], 'direction': 'entry', 'port_code': 'EBB',
        'country_code': 'UG', 'occurred_at': '2026-09-16T15:00:00Z',
        'source_authority': 'IMMIGRATION', 'provenance_reference': 'LEGACY-001',
    })
    assert response.status_code == 404
