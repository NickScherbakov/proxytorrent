"""Authentication and security middleware."""
import hashlib
import hmac
import logging
from typing import Optional

from fastapi import Header, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def verify_hmac_signature(
    request: Request,
    x_signature: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Verify HMAC signature for request.

    Args:
        request: FastAPI request
        x_signature: HMAC signature from header

    Returns:
        User ID if authenticated, None otherwise

    Raises:
        HTTPException: If auth is required but invalid
    """
    if not settings.security.auth_enabled:
        return None

    # Check bearer token first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token in settings.security.bearer_tokens:
            return f"token:{token[:8]}"

    # Check HMAC signature
    if x_signature:
        # Get request body
        body = await request.body()

        # Compute expected signature
        expected_signature = hmac.new(
            settings.security.hmac_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if hmac.compare_digest(x_signature, expected_signature):
            # Use IP as user ID for HMAC auth
            client_ip = request.client.host if request.client else "unknown"
            return f"hmac:{client_ip}"

    # Auth required but not provided/invalid
    if settings.security.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return None


async def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check X-Forwarded-For header (behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Use direct client IP
    if request.client:
        return request.client.host

    return "unknown"
