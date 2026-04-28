"""Pytest configuration and shared fixtures for backend tests."""

import pytest
import httpx


@pytest.fixture(scope="session")
def qdrant_available() -> bool:
    """Return True if a local Qdrant instance is reachable, False otherwise.

    Tests that depend on Qdrant should use this fixture and skip if False:

        def test_something(qdrant_available):
            if not qdrant_available:
                pytest.skip("Qdrant not reachable")
    """
    try:
        resp = httpx.get("http://localhost:6333/healthz", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False
