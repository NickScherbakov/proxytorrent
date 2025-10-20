"""HTTP fetcher service with proxy support."""
import hashlib
import logging
from typing import Optional

import aiohttp
from aiohttp_socks import ProxyConnector

from app.core.config import settings

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Base exception for fetch errors."""

    pass


class FetchTimeoutError(FetchError):
    """Fetch timeout error."""

    pass


class FetchSizeError(FetchError):
    """Response size exceeds limit."""

    pass


class FetchMimeError(FetchError):
    """Invalid MIME type."""

    pass


class FetchResult:
    """Result of a fetch operation."""

    def __init__(
        self,
        content: bytes,
        content_type: str,
        status_code: int,
        headers: dict[str, str],
        url: str,
    ):
        self.content = content
        self.content_type = content_type
        self.status_code = status_code
        self.headers = headers
        self.url = url
        self._content_hash: Optional[str] = None

    @property
    def content_hash(self) -> str:
        """Compute SHA256 hash of content."""
        if self._content_hash is None:
            self._content_hash = hashlib.sha256(self.content).hexdigest()
        return self._content_hash

    @property
    def content_size(self) -> int:
        """Get content size in bytes."""
        return len(self.content)


class Fetcher:
    """HTTP fetcher with proxy and security features."""

    def __init__(self) -> None:
        """Initialize fetcher."""
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            connector = None

            # Configure proxy if enabled
            if settings.proxy.proxy_enabled and settings.proxy.proxy_url:
                logger.info(f"Using proxy: {settings.proxy.proxy_type}://{settings.proxy.proxy_host}:{settings.proxy.proxy_port}")
                connector = ProxyConnector.from_url(settings.proxy.proxy_url)

            timeout = aiohttp.ClientTimeout(
                total=settings.fetcher.connect_timeout + settings.fetcher.read_timeout,
                connect=settings.fetcher.connect_timeout,
                sock_read=settings.fetcher.read_timeout,
            )

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": settings.fetcher.user_agent},
            )

        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _validate_mime_type(self, content_type: str) -> bool:
        """Check if MIME type is allowed."""
        if not content_type:
            return False

        content_type = content_type.split(";")[0].strip().lower()

        for allowed in settings.fetcher.mime_whitelist:
            if allowed.endswith("/*"):
                # Wildcard match
                prefix = allowed[:-2]
                if content_type.startswith(prefix):
                    return True
            elif content_type == allowed.lower():
                return True

        return False

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> FetchResult:
        """
        Fetch URL through proxy with security checks.

        Args:
            url: URL to fetch
            method: HTTP method
            headers: Optional custom headers
            body: Optional request body

        Returns:
            FetchResult with content and metadata

        Raises:
            FetchError: On fetch failure
            FetchTimeoutError: On timeout
            FetchSizeError: If response too large
            FetchMimeError: If MIME type not allowed
        """
        session = await self._get_session()

        request_headers = headers.copy() if headers else {}

        try:
            logger.info(f"Fetching {method} {url}")

            async with session.request(
                method,
                url,
                headers=request_headers,
                data=body,
                ssl=settings.fetcher.verify_ssl,
            ) as response:
                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if not self._validate_mime_type(content_type):
                    raise FetchMimeError(
                        f"MIME type not allowed: {content_type}"
                    )

                # Check content length header
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > settings.fetcher.max_size:
                    raise FetchSizeError(
                        f"Content size {content_length} exceeds limit {settings.fetcher.max_size}"
                    )

                # Read content with size limit
                chunks = []
                total_size = 0

                async for chunk in response.content.iter_chunked(8192):
                    total_size += len(chunk)
                    if total_size > settings.fetcher.max_size:
                        raise FetchSizeError(
                            f"Content size exceeds limit {settings.fetcher.max_size}"
                        )
                    chunks.append(chunk)

                content = b"".join(chunks)

                logger.info(
                    f"Fetched {len(content)} bytes from {url} "
                    f"(status={response.status}, type={content_type})"
                )

                return FetchResult(
                    content=content,
                    content_type=content_type,
                    status_code=response.status,
                    headers=dict(response.headers),
                    url=str(response.url),
                )

        except aiohttp.ClientError as e:
            logger.error(f"Fetch error for {url}: {e}")
            raise FetchError(f"Failed to fetch {url}: {e}") from e
        except TimeoutError as e:
            logger.error(f"Timeout fetching {url}")
            raise FetchTimeoutError(f"Timeout fetching {url}") from e


# Global fetcher instance
_fetcher: Optional[Fetcher] = None


async def get_fetcher() -> Fetcher:
    """Get global fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = Fetcher()
    return _fetcher


async def close_fetcher() -> None:
    """Close global fetcher instance."""
    global _fetcher
    if _fetcher:
        await _fetcher.close()
        _fetcher = None
