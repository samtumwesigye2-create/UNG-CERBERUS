"""Enrollment was superseded by passport-only verification on 2026-09-16."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.parametrize('path', ['/v1/biometrics/enrollments', '/v1/biometrics/identifications'])
def test_enrollment_and_registry_search_are_not_exposed(path):
    with TestClient(app) as client:
        response = client.post(path, json={'person_id': 1, 'sample_reference': 'synthetic://sample'})
        assert response.status_code == 404
