"""Tests for the semantic cache layer and cache invalidation.

Run with: pytest backend/tests/api/test_cache.py -v
"""

from __future__ import annotations

import json
import math
import uuid

import pytest
import pytest_asyncio

try:
    import fakeredis.aioredis as fakeredis_aio

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False

from backend.api.pipeline.cache import CacheLayer, _STATS_KEY
from backend.ingestion.invalidator import CacheInvalidator

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unit_vec(dim: int, index: int) -> list[float]:
    """Return a unit vector of length *dim* with only index *index* set."""
    v = [0.0] * dim
    v[index] = 1.0
    return v


def _normalize(v: list[float]) -> list[float]:
    mag = math.sqrt(sum(x * x for x in v))
    return [x / mag for x in v]


def _identical_embedding(n: int = 4) -> list[float]:
    return _normalize([1.0] * n)


def _orthogonal_embedding(n: int = 4) -> list[float]:
    return _unit_vec(n, 0)


def _another_orthogonal(n: int = 4) -> list[float]:
    return _unit_vec(n, 1)


@pytest.fixture
def fake_redis():
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    return fakeredis_aio.FakeRedis(decode_responses=True)


@pytest.fixture
def cache(fake_redis):
    return CacheLayer(redis_client=fake_redis, embedder=None, threshold=0.92)


# ---------------------------------------------------------------------------
# cache.set() — main key + secondary index
# ---------------------------------------------------------------------------


async def test_set_writes_main_key(cache, fake_redis):
    qid = str(uuid.uuid4())
    emb = _identical_embedding()
    await cache.set(qid, ["src-1", "src-2"], emb, "answer", [], 0.9)

    entry = await fake_redis.hgetall(f"cache:query:{qid}")
    assert entry["answer"] == "answer"
    assert json.loads(entry["embedding"]) == emb
    assert json.loads(entry["source_ids"]) == ["src-1", "src-2"]


async def test_set_writes_secondary_index_keys(cache, fake_redis):
    qid = str(uuid.uuid4())
    await cache.set(qid, ["src-a", "src-b"], _identical_embedding(), "ans", [], 0.8)

    val_a = await fake_redis.get(f"cache:src_idx:src-a:{qid}")
    val_b = await fake_redis.get(f"cache:src_idx:src-b:{qid}")
    assert val_a == qid
    assert val_b == qid


async def test_set_applies_ttl(cache, fake_redis):
    qid = str(uuid.uuid4())
    await cache.set(qid, ["src-1"], _identical_embedding(), "ans", [], 0.9)

    ttl_main = await fake_redis.ttl(f"cache:query:{qid}")
    ttl_idx = await fake_redis.ttl(f"cache:src_idx:src-1:{qid}")
    # TTL should be set (> 0) and close to 86400
    assert ttl_main > 0
    assert ttl_idx > 0


# ---------------------------------------------------------------------------
# cache.get() — hit / miss
# ---------------------------------------------------------------------------


async def test_get_returns_hit_on_identical_embedding(cache, fake_redis):
    qid = str(uuid.uuid4())
    emb = _identical_embedding()
    await cache.set(qid, ["src-1"], emb, "cached answer", [{"ref": 1}], 0.95)

    result = await cache.get(emb, str(uuid.uuid4()))
    assert result is not None
    assert result.answer == "cached answer"
    assert result.cached is True
    assert result.confidence == 0.95


async def test_get_returns_none_on_orthogonal_embedding(cache, fake_redis):
    qid = str(uuid.uuid4())
    stored_emb = _orthogonal_embedding()
    query_emb = _another_orthogonal()

    await cache.set(qid, ["src-1"], stored_emb, "answer", [], 0.9)

    result = await cache.get(query_emb, str(uuid.uuid4()))
    assert result is None


async def test_get_returns_none_on_empty_cache(cache):
    result = await cache.get(_identical_embedding(), str(uuid.uuid4()))
    assert result is None


# ---------------------------------------------------------------------------
# Stats tracking
# ---------------------------------------------------------------------------


async def test_hit_increments_counter(cache, fake_redis):
    qid = str(uuid.uuid4())
    emb = _identical_embedding()
    await cache.set(qid, ["src-1"], emb, "ans", [], 0.9)

    await cache.get(emb, str(uuid.uuid4()))

    raw = await fake_redis.hgetall(_STATS_KEY)
    assert int(raw.get("hits", 0)) >= 1


async def test_miss_increments_counter(cache, fake_redis):
    # Empty cache → miss
    await cache.get(_identical_embedding(), str(uuid.uuid4()))

    raw = await fake_redis.hgetall(_STATS_KEY)
    assert int(raw.get("misses", 0)) >= 1


async def test_get_stats_returns_hit_rate(cache, fake_redis):
    qid = str(uuid.uuid4())
    emb = _identical_embedding()
    await cache.set(qid, ["src-1"], emb, "ans", [], 0.9)

    # 1 hit, 0 misses
    await cache.get(emb, str(uuid.uuid4()))
    stats = await cache.get_stats()
    assert stats["hits"] == 1
    assert stats["hit_rate"] == 1.0


async def test_get_stats_with_no_data(cache):
    stats = await cache.get_stats()
    assert stats["hit_rate"] is None
    assert stats["hits"] == 0
    assert stats["misses"] == 0


# ---------------------------------------------------------------------------
# CacheInvalidator
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_redis_invalidator():
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    return fakeredis_aio.FakeRedis(decode_responses=True)


@pytest.fixture
def invalidator(fake_redis_invalidator, monkeypatch):
    inv = CacheInvalidator.__new__(CacheInvalidator)
    inv.redis = fake_redis_invalidator
    return inv


async def test_invalidate_source_deletes_main_and_index_keys(invalidator, fake_redis_invalidator):
    qid = str(uuid.uuid4())
    source_id = "doc-42"

    # Write main + index manually
    await fake_redis_invalidator.hset(f"cache:query:{qid}", mapping={"answer": "x"})
    await fake_redis_invalidator.set(f"cache:src_idx:{source_id}:{qid}", qid)

    deleted = await invalidator.invalidate_source(source_id)

    assert deleted == 1
    assert await fake_redis_invalidator.exists(f"cache:query:{qid}") == 0
    assert await fake_redis_invalidator.exists(f"cache:src_idx:{source_id}:{qid}") == 0


async def test_invalidate_source_does_not_delete_other_sources(invalidator, fake_redis_invalidator):
    qid_a = str(uuid.uuid4())
    qid_b = str(uuid.uuid4())

    await fake_redis_invalidator.hset(f"cache:query:{qid_a}", mapping={"answer": "a"})
    await fake_redis_invalidator.set(f"cache:src_idx:src-target:{qid_a}", qid_a)

    await fake_redis_invalidator.hset(f"cache:query:{qid_b}", mapping={"answer": "b"})
    await fake_redis_invalidator.set(f"cache:src_idx:src-other:{qid_b}", qid_b)

    deleted = await invalidator.invalidate_source("src-target")

    assert deleted == 1
    # Other source's main key should still exist
    assert await fake_redis_invalidator.exists(f"cache:query:{qid_b}") == 1


async def test_invalidate_source_returns_zero_for_unknown_source(invalidator):
    deleted = await invalidator.invalidate_source("nonexistent-source")
    assert deleted == 0


# ---------------------------------------------------------------------------
# DELETE /v1/cache/invalidate — integration-style test
# ---------------------------------------------------------------------------


async def test_delete_cache_invalidate_endpoint():
    """Test the admin cache invalidation endpoint using TestClient."""
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")

    import fakeredis.aioredis as _fakeredis

    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.api.settings import settings

    fake_r = _fakeredis.FakeRedis(decode_responses=True)

    qid = str(uuid.uuid4())
    await fake_r.hset(f"cache:query:{qid}", mapping={"answer": "x"})
    await fake_r.set(f"cache:src_idx:my-source:{qid}", qid)

    app.state.redis = fake_r

    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.request(
            "DELETE",
            "/v1/cache/invalidate",
            json={"source_ids": ["my-source"]},
            headers={"X-API-Key": settings.ADMIN_API_KEY or "admin-key"},
        )

    # Cleanup
    app.state.redis = None

    assert resp.status_code == 200
    data = resp.json()
    assert "deleted" in data
