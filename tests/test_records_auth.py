"""Regression tests: records API authentication (batch A-core fix)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

TOKEN = 'records-test-token-000000000000000000000'


@pytest.fixture
def client(monkeypatch):
    for k in ('ENV', 'ENVIRONMENT', 'RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'CERBERUS_API_TOKEN'):
        monkeypatch.delenv(k, raising=False)
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


PERSON = {'primary_name': 'Test Person', 'source_authority': 'TEST'}


def test_records_api_requires_token_when_configured(client, monkeypatch):
    monkeypatch.setenv('CERBERUS_API_TOKEN', TOKEN)
    assert client.post('/v1/people', json=PERSON).status_code == 401
    assert client.post('/v1/people', json=PERSON, headers={'Authorization': 'Bearer wrong'}).status_code == 401
    r = client.post('/v1/people', json=PERSON, headers={'Authorization': f'Bearer {TOKEN}'})
    assert r.status_code == 201
    pid = r.json()['id']
    assert client.get(f'/v1/people/{pid}').status_code == 401
    assert client.get(f'/v1/people/{pid}', headers={'Authorization': f'Bearer {TOKEN}'}).status_code == 200
    for path, body in [('/v1/watchlist', {}), ('/v1/screenings', {}), ('/v1/screenings/1/adjudicate', {}), ('/v1/cases', {}), ('/v1/cases/1/transitions', {}), (f'/v1/people/{pid}/documents', {})]:
        assert client.post(path, json=body).status_code == 401, path
    assert client.get('/health').status_code == 200
    assert client.get('/v1/profiles/uganda').status_code == 200


def test_records_api_refused_in_production_without_token(client, monkeypatch):
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    assert client.post('/v1/people', json=PERSON).status_code == 503
    assert client.get('/v1/people/1').status_code == 503


def test_records_api_open_in_dev_without_token(client):
    assert client.post('/v1/people', json=PERSON).status_code == 201


def test_short_token_rejected(client, monkeypatch):
    monkeypatch.setenv('CERBERUS_API_TOKEN', 'short')
    assert client.post('/v1/people', json=PERSON, headers={'Authorization': 'Bearer short'}).status_code == 503
