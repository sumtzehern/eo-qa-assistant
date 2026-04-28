"""Auth middleware: API key validation and JWT verification."""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.api.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def require_api_key(
    api_key: str | None = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str:
    """Validate X-API-Key header or Bearer JWT. Returns caller tier string."""
    if api_key:
        if api_key == settings.ADMIN_API_KEY:
            return "admin"
        if api_key == settings.INTERNAL_API_KEY:
            return "internal"

    if credentials and credentials.scheme.lower() == "bearer":
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            tier: str = payload.get("tier", "customer")
            return tier
        except JWTError:
            pass

    raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def require_admin(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Require admin-level API key. Returns 'admin' or raises 403."""
    if api_key == settings.ADMIN_API_KEY:
        return "admin"
    raise HTTPException(status_code=403, detail="Admin access required")
