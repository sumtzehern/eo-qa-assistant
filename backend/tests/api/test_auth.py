"""Tests for auth middleware: API key validation and tier resolution."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.settings import settings

client = TestClient(app, raise_server_exceptions=False)


def test_missing_api_key_returns_401():
    """Request with no X-API-Key and no Bearer token must return 401."""
    resp = client.get("/v1/sources")
    assert resp.status_code == 401


def test_invalid_api_key_returns_401():
    """Request with a garbage API key must return 401."""
    resp = client.get("/v1/sources", headers={"X-API-Key": "totally-wrong-key"})
    assert resp.status_code == 401


def test_valid_internal_key_passes():
    """Internal API key must be accepted and return a non-401 response."""
    resp = client.get("/v1/sources", headers={"X-API-Key": settings.INTERNAL_API_KEY})
    assert resp.status_code not in (401, 403)


def test_admin_endpoint_rejects_internal_key():
    """Admin-only endpoint must reject the internal (non-admin) key with 403."""
    resp = client.get(
        "/v1/admin/eval/flagged", headers={"X-API-Key": settings.INTERNAL_API_KEY}
    )
    assert resp.status_code == 403


def test_admin_key_accepted_on_admin_endpoint():
    """Admin API key must be accepted on an admin-only endpoint."""
    resp = client.get(
        "/v1/admin/eval/flagged", headers={"X-API-Key": settings.ADMIN_API_KEY}
    )
    assert resp.status_code == 200
