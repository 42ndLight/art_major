"""
Tests for the health check endpoint.
"""
import json

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_returns_ok(client):
    """GET /health/ returns HTTP 200 with JSON {"status": "ok"}."""
    url = reverse("health")
    response = client.get(url)
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data == {"status": "ok"}


@pytest.mark.django_db
def test_health_no_auth_required(client):
    """Unauthenticated requests to /health/ must succeed (no redirect)."""
    url = reverse("health")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_content_type_is_json(client):
    """The health endpoint must return Content-Type: application/json."""
    url = reverse("health")
    response = client.get(url)
    assert "application/json" in response.get("Content-Type", "")
