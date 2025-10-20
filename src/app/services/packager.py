"""Torrent packager service."""
import json
import logging
from pathlib import Path
from typing import Optional

import libtorrent as lt

from app.core.config import settings
from app.services.fetcher import FetchResult

logger = logging.getLogger(__name__)


class PackageError(Exception):
    """Base exception for packaging errors."""

    pass


class TorrentPackage:
    """Torrent package metadata."""

    def __init__(
        self,
        torrent_path: Path,
        infohash: str,
        content_path: Path,
        content_hash: str,
        content_size: int,
    ):
        self.torrent_path = torrent_path
        self.infohash = infohash
        self.content_path = content_path
        self.content_hash = content_hash
        self.content_size = content_size

    @property
    def magnet_link(self) -> str:
        """Generate magnet link."""
        magnet = f"magnet:?xt=urn:btih:{self.infohash}"
        if settings.torrent.announce_url:
            magnet += f"&tr={settings.torrent.announce_url}"
        return magnet


class Packager:
    """Service to package fetched content into torrents."""

    def __init__(self) -> None:
        """Initialize packager."""
        # Ensure storage directories exist
        settings.initialize_storage()

    def _save_content(self, fetch_result: FetchResult) -> tuple[Path, Path]:
        """
        Save fetched content to storage.

        Returns:
            Tuple of (content_path, metadata_path)
        """
        content_hash = fetch_result.content_hash

        # Use content-addressable storage
        content_dir = settings.storage.content_path / content_hash[:2] / content_hash[2:4]
        content_dir.mkdir(parents=True, exist_ok=True)

        content_path = content_dir / "content"
        metadata_path = content_dir / "metadata.json"

        # Save content if not exists (deduplication)
        if not content_path.exists():
            content_path.write_bytes(fetch_result.content)
            logger.info(f"Saved content to {content_path}")

        # Save metadata
        metadata = {
            "url": fetch_result.url,
            "content_type": fetch_result.content_type,
            "content_size": fetch_result.content_size,
            "content_hash": content_hash,
            "status_code": fetch_result.status_code,
            "headers": fetch_result.headers,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2))

        return content_path, metadata_path

    def _create_torrent(self, content_path: Path, content_hash: str) -> tuple[Path, str]:
        """
        Create torrent file for content.

        Returns:
            Tuple of (torrent_path, infohash)
        """
        # Check if torrent already exists
        torrent_file = settings.storage.torrent_path / f"{content_hash}.torrent"

        if torrent_file.exists():
            # Load existing torrent to get infohash
            torrent_info = lt.torrent_info(str(torrent_file))
            infohash = str(torrent_info.info_hash())
            logger.info(f"Torrent already exists: {infohash}")
            return torrent_file, infohash

        # Create torrent
        fs = lt.file_storage()
        lt.add_files(fs, str(content_path))

        t = lt.create_torrent(fs, piece_size=settings.torrent.piece_size)

        # Set private flag
        if settings.torrent.private_tracker:
            t.set_priv(True)

        # Add tracker if configured
        if settings.torrent.announce_url:
            t.add_tracker(settings.torrent.announce_url)

        # Set creator
        t.set_creator("ProxyTorrent")

        # Generate torrent
        lt.set_piece_hashes(t, str(content_path.parent))
        torrent_data = lt.bencode(t.generate())

        # Save torrent file
        settings.storage.torrent_path.mkdir(parents=True, exist_ok=True)
        torrent_file.write_bytes(torrent_data)

        # Get infohash
        torrent_info = lt.torrent_info(str(torrent_file))
        infohash = str(torrent_info.info_hash())

        logger.info(f"Created torrent: {infohash} at {torrent_file}")

        return torrent_file, infohash

    async def package(
        self, fetch_result: FetchResult, request_id: str
    ) -> TorrentPackage:
        """
        Package fetch result into torrent.

        Args:
            fetch_result: Result from fetcher
            request_id: Request ID for tracking

        Returns:
            TorrentPackage with paths and metadata

        Raises:
            PackageError: On packaging failure
        """
        try:
            logger.info(f"Packaging content for request {request_id}")

            # Save content
            content_path, metadata_path = self._save_content(fetch_result)

            # Create torrent
            torrent_path, infohash = self._create_torrent(
                content_path, fetch_result.content_hash
            )

            package = TorrentPackage(
                torrent_path=torrent_path,
                infohash=infohash,
                content_path=content_path,
                content_hash=fetch_result.content_hash,
                content_size=fetch_result.content_size,
            )

            logger.info(f"Packaged request {request_id}: infohash={infohash}")

            return package

        except Exception as e:
            logger.error(f"Packaging error for request {request_id}: {e}")
            raise PackageError(f"Failed to package content: {e}") from e

    def get_torrent_path(self, content_hash: str) -> Optional[Path]:
        """Get torrent file path for content hash."""
        torrent_file = settings.storage.torrent_path / f"{content_hash}.torrent"
        return torrent_file if torrent_file.exists() else None


# Global packager instance
_packager: Optional[Packager] = None


def get_packager() -> Packager:
    """Get global packager instance."""
    global _packager
    if _packager is None:
        _packager = Packager()
    return _packager
