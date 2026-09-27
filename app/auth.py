"""Authentication dependency verifying the incoming Bearer token from the Even App."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

# HTTPBearer extracts "Authorization: Bearer <token>"
security = HTTPBearer(auto_error=False)


async def verify_proxy_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> str:
    """Verifies that the incoming request contains a valid Bearer token.

    If PROXY_API_KEY is left empty in settings, authentication is skipped (open proxy for testing).
    Otherwise, the Bearer token must strictly match PROXY_API_KEY.
    """
    if not settings.PROXY_API_KEY:
        # Dev convenience: if user hasn't configured a key yet, permit request
        return "unauthenticated"

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <PROXY_API_KEY> header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != settings.PROXY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PROXY_API_KEY token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
