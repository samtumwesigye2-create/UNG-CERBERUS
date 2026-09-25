from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_border_event_and_governed_watchlist_screening():
    with client:
        person = client.post('/v1/people', json={
            'primary_name': 'Amina Nakato', 'date_of_birth': '1990-01-02',
            'nationality': 'UG', 'citizenship': 'UG',
            'source_authority': 'IMMIGRATION', 'provenance_reference': 'ENROLL-002'
        }).json()

        event = client.post('/v1/border-events', json={
            'person_id': person['id'], 'direction': 'entry',
            'port_code': 'EBB', 'country_code': 'UG',
            'occurred_at': '2026-09-16T05:00:00Z',
            'source_authority': 'IMMIGRATION', 'provenance_reference': 'EBB-ENTRY-001'
        })
        assert event.status_code == 404

        future = (date.today() + timedelta(days=30)).isoformat()
        wl = client.post('/v1/watchlist', json={
            'subject_name': 'Amina Nakato', 'date_of_birth': '1990-01-02',
            'originating_authority': 'AUTHORIZED-UNIT', 'reason_category': 'manual_review',
            'legal_authority_reference': 'AUTH-001', 'valid_until': future,
            'provenance_reference': 'WL-001'
        })
        assert wl.status_code == 201

        screening = client.post('/v1/screenings', json={
            'person_id': person['id'], 'purpose': 'border_entry', 'actor_ref': 'OFFICER-01'
        })
        assert screening.status_code == 201
        body = screening.json()
        assert body['decision'] == 'pending_review'
        assert body['matches'][0]['confirmed_identity'] is False

        cleared = client.post(f"/v1/screenings/{body['id']}/adjudicate", json={
            'outcome': 'cleared', 'actor_ref': 'SUPERVISOR-01',
            'reason': 'False positive cleared after human review'
        })
        assert cleared.status_code == 200
        assert cleared.json()['decision'] == 'cleared'


def test_expired_watchlist_entry_is_not_active_match():
    with client:
        person = client.post('/v1/people', json={
            'primary_name': 'Expired Example', 'source_authority': 'IMMIGRATION'
        }).json()
        past = (date.today() - timedelta(days=1)).isoformat()
        client.post('/v1/watchlist', json={
            'subject_name': 'Expired Example', 'originating_authority': 'AUTHORIZED-UNIT',
            'reason_category': 'manual_review', 'legal_authority_reference': 'AUTH-OLD',
            'valid_until': past, 'provenance_reference': 'WL-OLD'
        })
        screening = client.post('/v1/screenings', json={
            'person_id': person['id'], 'purpose': 'border_entry', 'actor_ref': 'OFFICER-02'
        })
        assert screening.status_code == 201
        assert screening.json()['decision'] == 'no_active_match'
