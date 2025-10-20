"""API endpoints for fetch requests."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_client_ip, verify_hmac_signature
from app.api.ratelimit import get_rate_limiter
from app.core.database import get_db
from app.models.database import FetchRequest
from app.models.schemas import (
    CreateRequestPayload,
    CreateRequestResponse,
    MagnetLinkResponse,
    RequestStatus,
    RequestStatusResponse,
)
from app.services.packager import get_packager
from app.tasks.queue import get_task_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=CreateRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: CreateRequestPayload,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(verify_hmac_signature)] = None,
) -> CreateRequestResponse:
    """
    Create a new fetch request.

    Accepts a URL to fetch through proxy and package as torrent.
    Requires authentication via HMAC signature or bearer token.
    """
    # Get client IP
    client_ip = await get_client_ip(request)

    # Check rate limits
    rate_limiter = get_rate_limiter()
    rate_limiter.check_rate_limit(user_id, client_ip)

    # Create database record
    fetch_request = FetchRequest(
        status=RequestStatus.QUEUED.value,
        url=str(payload.url),
        method=payload.method.value,
        headers=payload.headers,
        body=payload.body,
        ttl=payload.ttl,
        user_id=user_id,
        client_ip=client_ip,
        progress=0,
    )

    db.add(fetch_request)
    await db.commit()
    await db.refresh(fetch_request)

    # Enqueue for processing
    task_queue = get_task_queue()
    await task_queue.enqueue(fetch_request.id)

    logger.info(f"Created request {fetch_request.id} for {payload.url}")

    return CreateRequestResponse(
        id=fetch_request.id,
        status=RequestStatus(fetch_request.status),
        estimated_ready=60,  # Estimated 1 minute
        created_at=fetch_request.created_at,
    )


@router.get("/{request_id}", response_model=RequestStatusResponse)
async def get_request_status(
    request_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(verify_hmac_signature)] = None,
) -> RequestStatusResponse:
    """Get the status of a fetch request."""
    result = await db.execute(
        select(FetchRequest).where(FetchRequest.id == request_id)
    )
    fetch_request = result.scalar_one_or_none()

    if not fetch_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found",
        )

    return RequestStatusResponse(
        id=fetch_request.id,
        status=RequestStatus(fetch_request.status),
        url=fetch_request.url,
        method=fetch_request.method,
        created_at=fetch_request.created_at,
        updated_at=fetch_request.updated_at,
        completed_at=fetch_request.completed_at,
        infohash=fetch_request.infohash,
        content_hash=fetch_request.content_hash,
        content_size=fetch_request.content_size,
        content_type=fetch_request.content_type,
        error_message=fetch_request.error_message,
        progress=fetch_request.progress,
    )


@router.get("/{request_id}/torrent", response_class=FileResponse)
async def get_torrent_file(
    request_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(verify_hmac_signature)] = None,
) -> FileResponse:
    """Download the .torrent file for a completed request."""
    result = await db.execute(
        select(FetchRequest).where(FetchRequest.id == request_id)
    )
    fetch_request = result.scalar_one_or_none()

    if not fetch_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found",
        )

    if fetch_request.status != RequestStatus.READY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request not ready (status: {fetch_request.status})",
        )

    if not fetch_request.torrent_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Torrent file path not set",
        )

    return FileResponse(
        path=fetch_request.torrent_path,
        filename=f"{fetch_request.infohash}.torrent",
        media_type="application/x-bittorrent",
    )


@router.get("/{request_id}/magnet", response_model=MagnetLinkResponse)
async def get_magnet_link(
    request_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(verify_hmac_signature)] = None,
) -> MagnetLinkResponse:
    """Get the magnet link for a completed request."""
    result = await db.execute(
        select(FetchRequest).where(FetchRequest.id == request_id)
    )
    fetch_request = result.scalar_one_or_none()

    if not fetch_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found",
        )

    if fetch_request.status != RequestStatus.READY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request not ready (status: {fetch_request.status})",
        )

    if not fetch_request.infohash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Infohash not set",
        )

    # Build magnet link
    packager = get_packager()
    torrent_path = packager.get_torrent_path(fetch_request.content_hash)
    if not torrent_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Torrent file not found",
        )

    # Use packager to build proper magnet link
    from app.services.packager import TorrentPackage
    from pathlib import Path

    package = TorrentPackage(
        torrent_path=Path(fetch_request.torrent_path),
        infohash=fetch_request.infohash,
        content_path=Path(""),  # Not needed for magnet link
        content_hash=fetch_request.content_hash,
        content_size=fetch_request.content_size or 0,
    )

    return MagnetLinkResponse(
        id=fetch_request.id,
        magnet_link=package.magnet_link,
        infohash=fetch_request.infohash,
    )


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_request(
    request_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str | None, Depends(verify_hmac_signature)] = None,
) -> None:
    """Cancel or remove a fetch request."""
    result = await db.execute(
        select(FetchRequest).where(FetchRequest.id == request_id)
    )
    fetch_request = result.scalar_one_or_none()

    if not fetch_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found",
        )

    # Update status to cancelled
    fetch_request.status = RequestStatus.CANCELLED.value
    fetch_request.updated_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Cancelled request {request_id}")
