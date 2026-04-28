"""Tests for route stubs: health, query, sources, eval."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.settings import settings

client = TestClient(app, raise_server_exceptions=False)

AUTH = {"X-API-Key": settings.INTERNAL_API_KEY}
ADMIN_AUTH = {"X-API-Key": settings.ADMIN_API_KEY}


def test_health_returns_200():
    """Health endpoint must return 200 with status=ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "services" in data


def test_query_stub_returns_200_with_valid_key():
    """/v1/query with a valid key should return 200 and an SSE stream."""
    resp = client.post(
        "/v1/query",
        json={"query": "What is EdgeOne?"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    # The SSE body must contain at least one 'data:' line.
    assert b"data:" in resp.content

    # Parse the final 'done' event.
    lines = resp.content.decode().splitlines()
    done_line = next((l for l in lines if '"done": true' in l or '"done":true' in l), None)
    assert done_line is not None, "No 'done' event found in SSE stream"
    payload = json.loads(done_line.removeprefix("data: ").strip())
    assert "query_id" in payload
    assert "answer" in payload


def test_query_rejects_empty_string():
    """/v1/query must return 422 when the query field is an empty string."""
    resp = client.post(
        "/v1/query",
        json={"query": ""},
        headers=AUTH,
    )
    assert resp.status_code == 422


def test_query_rejects_missing_query_field():
    """/v1/query must return 422 when the query field is absent."""
    resp = client.post("/v1/query", json={}, headers=AUTH)
    assert resp.status_code == 422


def test_sources_returns_list():
    """/v1/sources must return a list with a non-negative total."""
    resp = client.get("/v1/sources", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert data["total"] >= 0


def test_eval_summary_returns_200():
    """/v1/eval/summary must be accessible with internal key."""
    resp = client.get("/v1/eval/summary", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_queries" in data


def test_query_eval_stub_returns_200():
    """/v1/query/{id}/eval must return 200 with a pending status."""
    resp = client.get("/v1/query/fake-id/eval", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["query_id"] == "fake-id"


def test_ingestion_trigger_requires_admin():
    """POST /v1/ingestion/trigger must require admin key."""
    resp = client.post(
        "/v1/ingestion/trigger",
        json={},
        headers=AUTH,  # internal key, not admin
    )
    assert resp.status_code == 403


def test_ingestion_trigger_with_admin_key():
    """POST /v1/ingestion/trigger with admin key must return 202."""
    resp = client.post(
        "/v1/ingestion/trigger",
        json={},
        headers=ADMIN_AUTH,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_ids" in data
    assert len(data["job_ids"]) > 0
