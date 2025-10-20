"""Pydantic models for API requests and responses."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class RequestMethod(str, Enum):
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class RequestStatus(str, Enum):
    """Request processing status."""

    QUEUED = "queued"
    FETCHING = "fetching"
    PACKAGING = "packaging"
    SEEDING = "seeding"
    READY = "ready"
    ERROR = "error"
    CANCELLED = "cancelled"


class CreateRequestPayload(BaseModel):
    """Payload for creating a new fetch request."""

    url: HttpUrl = Field(..., description="URL to fetch")
    method: RequestMethod = Field(default=RequestMethod.GET, description="HTTP method")
    headers: Optional[dict[str, str]] = Field(
        default=None, description="Custom HTTP headers"
    )
    body: Optional[str] = Field(default=None, description="Request body (for POST/PUT)")
    ttl: int = Field(
        default=3600, ge=0, le=86400, description="Cache TTL in seconds"
    )

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: Optional[dict[str, str]]) -> Optional[dict[str, str]]:
        """Validate headers."""
        if v is None:
            return None
        # Remove sensitive headers
        sensitive = ["authorization", "cookie", "x-signature"]
        return {k: val for k, val in v.items() if k.lower() not in sensitive}


class CreateRequestResponse(BaseModel):
    """Response after creating a fetch request."""

    id: str = Field(..., description="Unique request ID")
    status: RequestStatus = Field(..., description="Current status")
    estimated_ready: Optional[int] = Field(
        default=None, description="Estimated time to ready (seconds)"
    )
    created_at: datetime = Field(..., description="Creation timestamp")


class RequestStatusResponse(BaseModel):
    """Response for request status query."""

    id: str = Field(..., description="Request ID")
    status: RequestStatus = Field(..., description="Current status")
    url: str = Field(..., description="Original URL")
    method: RequestMethod = Field(..., description="HTTP method")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion timestamp"
    )
    infohash: Optional[str] = Field(default=None, description="Torrent infohash")
    content_hash: Optional[str] = Field(default=None, description="Content SHA256 hash")
    content_size: Optional[int] = Field(default=None, description="Content size in bytes")
    content_type: Optional[str] = Field(default=None, description="Content MIME type")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")


class MagnetLinkResponse(BaseModel):
    """Response containing magnet link."""

    id: str = Field(..., description="Request ID")
    magnet_link: str = Field(..., description="Magnet URI")
    infohash: str = Field(..., description="Torrent infohash")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Uptime in seconds")
    checks: dict[str, Any] = Field(..., description="Component health checks")


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[Any] = Field(default=None, description="Additional error details")
