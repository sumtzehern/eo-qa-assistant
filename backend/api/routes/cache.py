"""Cache management routes."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request

from backend.api.middleware.auth import require_admin
from backend.api.pipeline.cache import CacheLayer
from backend.ingestion.invalidator import CacheInvalidator

router = APIRouter()


class InvalidateRequest(BaseModel):
    source_ids: list[str] | None = None  # None = clear all


class InvalidateResponse(BaseModel):
    deleted: int
    request_id: str | None = None


@router.delete("/cache/invalidate", response_model=InvalidateResponse, status_code=200)
async def invalidate_cache(
    body: InvalidateRequest,
    request: Request,
    _: str = Depends(require_admin),
) -> InvalidateResponse:
    """Invalidate cache entries. Pass source_ids to target specific sources, or omit to clear all."""
    redis_client = getattr(request.app.state, "redis", None)
    deleted = 0

    if body.source_ids is not None:
        # Invalidate per source via the secondary index
        invalidator = CacheInvalidator()
        try:
            for source_id in body.source_ids:
                deleted += await invalidator.invalidate_source(source_id)
        finally:
            await invalidator.close()
    else:
        # Clear ALL cache:query:* and cache:src_idx:* keys
        if redis_client is not None:
            async for key in redis_client.scan_iter("cache:query:*"):
                await redis_client.delete(key)
                deleted += 1
            async for key in redis_client.scan_iter("cache:src_idx:*"):
                await redis_client.delete(key)

    return InvalidateResponse(
        deleted=deleted,
        request_id=getattr(request.state, "request_id", None),
    )
