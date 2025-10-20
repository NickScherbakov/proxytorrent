"""BitTorrent seeder service using libtorrent."""
import logging
from pathlib import Path

import libtorrent as lt

from app.core.config import settings

logger = logging.getLogger(__name__)


class SeederError(Exception):
    """Base exception for seeder errors."""

    pass


class Seeder:
    """BitTorrent seeder using libtorrent."""

    def __init__(self) -> None:
        """Initialize seeder."""
        self._session: lt.session | None = None
        self._torrents: dict[str, lt.torrent_handle] = {}
        self._initialize_session()

    def _initialize_session(self) -> None:
        """Initialize libtorrent session."""
        logger.info("Initializing libtorrent session")

        # Create session with settings
        session_params = lt.session_params()

        # Apply settings
        session_settings = {
            "enable_dht": False,  # Private torrents don't use DHT
            "enable_lsd": False,  # Disable local service discovery
            "enable_upnp": False,
            "enable_natpmp": False,
            "anonymous_mode": True,  # Enhanced privacy
        }

        # Set rate limits if configured
        if settings.torrent.upload_rate_limit > 0:
            session_settings["upload_rate_limit"] = settings.torrent.upload_rate_limit

        if settings.torrent.download_rate_limit > 0:
            session_settings["download_rate_limit"] = settings.torrent.download_rate_limit

        # Set connection limits
        session_settings["connections_limit"] = settings.torrent.max_connections

        # Encryption settings
        if settings.torrent.encryption_enabled:
            session_settings["out_enc_policy"] = lt.enc_policy.enabled
            session_settings["in_enc_policy"] = lt.enc_policy.enabled
            session_settings["allowed_enc_level"] = lt.enc_level.both
        else:
            session_settings["out_enc_policy"] = lt.enc_policy.disabled
            session_settings["in_enc_policy"] = lt.enc_policy.disabled

        session_params.settings = session_settings

        self._session = lt.session(session_params)

        # Set alert mask to get important alerts
        self._session.set_alert_mask(
            lt.alert.category_t.error_notification
            | lt.alert.category_t.status_notification
            | lt.alert.category_t.storage_notification
        )

        logger.info("Libtorrent session initialized")

    def add_torrent(
        self, torrent_path: Path, content_path: Path, infohash: str
    ) -> None:
        """
        Add torrent to seeder.

        Args:
            torrent_path: Path to .torrent file
            content_path: Path to content file
            infohash: Torrent infohash

        Raises:
            SeederError: On seeding failure
        """
        if not self._session:
            raise SeederError("Session not initialized")

        if infohash in self._torrents:
            logger.info(f"Torrent {infohash} already seeding")
            return

        try:
            # Load torrent info
            torrent_info = lt.torrent_info(str(torrent_path))

            # Create add_torrent_params
            atp = lt.add_torrent_params()
            atp.ti = torrent_info
            atp.save_path = str(content_path.parent)

            # Seed mode (we already have complete file)
            atp.flags |= lt.torrent_flags.seed_mode

            # Check for existing resume data
            resume_file = settings.storage.resume_path / f"{infohash}.resume"
            if resume_file.exists():
                try:
                    resume_data = resume_file.read_bytes()
                    atp.resume_data = resume_data
                    logger.info(f"Loaded resume data for {infohash}")
                except Exception as e:
                    logger.warning(f"Failed to load resume data: {e}")

            # Add torrent to session
            handle = self._session.add_torrent(atp)
            self._torrents[infohash] = handle

            logger.info(f"Added torrent {infohash} for seeding")

        except Exception as e:
            logger.error(f"Failed to add torrent {infohash}: {e}")
            raise SeederError(f"Failed to add torrent: {e}") from e

    def remove_torrent(self, infohash: str, delete_files: bool = False) -> None:
        """
        Remove torrent from seeder.

        Args:
            infohash: Torrent infohash
            delete_files: Whether to delete files
        """
        if not self._session or infohash not in self._torrents:
            return

        try:
            handle = self._torrents[infohash]

            # Save resume data
            self._save_resume_data(infohash, handle)

            # Remove torrent
            if delete_files:
                self._session.remove_torrent(handle, lt.session.delete_files)
            else:
                self._session.remove_torrent(handle)

            del self._torrents[infohash]

            logger.info(f"Removed torrent {infohash}")

        except Exception as e:
            logger.error(f"Failed to remove torrent {infohash}: {e}")

    def _save_resume_data(
        self, infohash: str, handle: lt.torrent_handle
    ) -> None:
        """Save resume data for torrent."""
        try:
            # Request resume data
            handle.save_resume_data(lt.torrent_handle.only_if_modified)

            # Wait for alert (with timeout)
            alerts = self._session.pop_alerts()
            for alert in alerts:
                if isinstance(alert, lt.save_resume_data_alert):
                    if str(alert.handle.info_hash()) == infohash:
                        # Save resume data
                        resume_file = settings.storage.resume_path / f"{infohash}.resume"
                        settings.storage.resume_path.mkdir(parents=True, exist_ok=True)
                        resume_file.write_bytes(lt.write_resume_data(alert.params))
                        logger.debug(f"Saved resume data for {infohash}")
                        break

        except Exception as e:
            logger.warning(f"Failed to save resume data for {infohash}: {e}")

    def get_status(self, infohash: str) -> dict | None:
        """Get torrent status."""
        if not self._session or infohash not in self._torrents:
            return None

        try:
            handle = self._torrents[infohash]
            status = handle.status()

            return {
                "state": str(status.state),
                "progress": status.progress,
                "upload_rate": status.upload_rate,
                "download_rate": status.download_rate,
                "num_peers": status.num_peers,
                "num_seeds": status.num_seeds,
                "total_upload": status.total_upload,
                "total_download": status.total_download,
            }
        except Exception as e:
            logger.error(f"Failed to get status for {infohash}: {e}")
            return None

    def save_all_resume_data(self) -> None:
        """Save resume data for all torrents."""
        if not self._session:
            return

        logger.info("Saving resume data for all torrents")
        for infohash, handle in self._torrents.items():
            self._save_resume_data(infohash, handle)

    def shutdown(self) -> None:
        """Shutdown seeder gracefully."""
        if not self._session:
            return

        logger.info("Shutting down seeder")

        # Save all resume data
        self.save_all_resume_data()

        # Remove all torrents
        for infohash in list(self._torrents.keys()):
            self.remove_torrent(infohash, delete_files=False)

        self._session = None
        logger.info("Seeder shut down")


# Global seeder instance
_seeder: Seeder | None = None


def get_seeder() -> Seeder:
    """Get global seeder instance."""
    global _seeder
    if _seeder is None:
        _seeder = Seeder()
    return _seeder


def shutdown_seeder() -> None:
    """Shutdown global seeder instance."""
    global _seeder
    if _seeder:
        _seeder.shutdown()
        _seeder = None
