"""Tests for fetcher service."""
from unittest.mock import AsyncMock

import pytest

from app.services.fetcher import (
    Fetcher,
    FetchMimeError,
)


@pytest.mark.asyncio
async def test_fetcher_validate_mime_type():
    """Test MIME type validation."""
    fetcher = Fetcher()

    # Valid MIME types
    assert fetcher._validate_mime_type("text/html")
    assert fetcher._validate_mime_type("text/plain")
    assert fetcher._validate_mime_type("application/json")
    assert fetcher._validate_mime_type("image/png")
    assert fetcher._validate_mime_type("image/jpeg")

    # Invalid MIME types
    assert not fetcher._validate_mime_type("application/x-executable")
    assert not fetcher._validate_mime_type("video/mp4")


@pytest.mark.asyncio
async def test_fetcher_fetch_success(mocker):
    """Test successful fetch."""
    # Mock aiohttp response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.url = "http://example.com"

    async def mock_iter():
        yield b"test content"

    mock_response.content.iter_chunked = lambda size: mock_iter()

    # Mock session
    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    fetcher = Fetcher()
    fetcher._session = mock_session

    # Fetch
    result = await fetcher.fetch("http://example.com")

    assert result.content == b"test content"
    assert result.status_code == 200
    assert result.content_type == "text/html"
    assert len(result.content_hash) == 64  # SHA256 hex


@pytest.mark.asyncio
async def test_fetcher_mime_error(mocker):
    """Test MIME type error."""
    # Mock aiohttp response with invalid MIME
    mock_response = AsyncMock()
    mock_response.headers = {"Content-Type": "application/x-executable"}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    fetcher = Fetcher()
    fetcher._session = mock_session

    # Should raise FetchMimeError
    with pytest.raises(FetchMimeError):
        await fetcher.fetch("http://example.com")
