"""EdgeOne QA Assistant — FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.middleware.rate_limit import set_redis_client
from backend.api.routes import eval, ingestion, query, sources
from backend.api.settings import settings
from backend.db.session import init_db

# ---------------------------------------------------------------------------
# Lifespan: startup + shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    await init_db()

    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        set_redis_client(redis_client)
        app.state.redis = redis_client
    except Exception:
        # Redis unavailable — rate limiting is disabled; log and continue.
        app.state.redis = None

    yield

    # Shutdown
    if getattr(app.state, "redis", None):
        await app.state.redis.aclose()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="EdgeOne QA Assistant",
    description="RAG-based Q&A assistant for EdgeOne documentation.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    """Inject a unique request_id into every request's state."""
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": str(exc.detail) if hasattr(exc, "detail") else "Unauthorized",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "detail": str(exc.detail) if hasattr(exc, "detail") else "Forbidden",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded",
            "request_id": getattr(request.state, "request_id", None),
        },
        headers={"Retry-After": "60"},
    )


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors() if hasattr(exc, "errors") else str(exc),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(query.router, prefix="/v1", tags=["query"])
app.include_router(sources.router, prefix="/v1", tags=["sources"])
app.include_router(eval.router, prefix="/v1", tags=["eval"])
app.include_router(ingestion.router, prefix="/v1", tags=["ingestion"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health(request: Request) -> dict:
    """Health check: reports FastAPI + Redis status."""
    redis_ok = False
    if getattr(app.state, "redis", None):
        try:
            await app.state.redis.ping()
            redis_ok = True
        except Exception:
            pass

    return {
        "status": "ok",
        "services": {
            "api": "ok",
            "redis": "ok" if redis_ok else "unavailable",
        },
        "request_id": request.state.request_id,
    }
