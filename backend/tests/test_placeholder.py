"""Placeholder test suite — passes CI gate before real tests are written.

These tests verify the FastAPI app and database models can be imported
and the health endpoint responds correctly. Replace with real tests in
Phase 2b.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    """Health check returns 200 OK with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_accessible(client: TestClient) -> None:
    """OpenAPI schema endpoint is accessible (confirms FastAPI setup)."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "EdgeOne QA Assistant"


def test_models_importable() -> None:
    """SQLAlchemy models can be imported without errors."""
    from db.models import Chunk, EvalResult, IngestionJob, Query

    assert Chunk.__tablename__ == "chunks"
    assert Query.__tablename__ == "queries"
    assert EvalResult.__tablename__ == "eval_results"
    assert IngestionJob.__tablename__ == "ingestion_jobs"
