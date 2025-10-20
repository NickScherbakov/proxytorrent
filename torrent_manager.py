"""
Torrent creation and management module.
"""

import logging
import hashlib
import time
from pathlib import Path
import libtorrent as lt

from config import TORRENT_DIR, SEED_TIME_HOURS, MAX_UPLOAD_RATE_KB, MAX_DOWNLOAD_RATE_KB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TorrentManager:
    """Handles torrent creation and seeding."""
    
    def __init__(self):
        self.session = lt.session()
        self._configure_session()
        self.active_torrents = {}
    
    def _configure_session(self):
        """Configure libtorrent session settings."""
        settings = {
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
        }
        
        if MAX_UPLOAD_RATE_KB > 0:
            settings['upload_rate_limit'] = MAX_UPLOAD_RATE_KB * 1024
        
        if MAX_DOWNLOAD_RATE_KB > 0:
            settings['download_rate_limit'] = MAX_DOWNLOAD_RATE_KB * 1024
        
        self.session.apply_settings(settings)
        
        # Add DHT routers
        self.session.add_dht_router("router.bittorrent.com", 6881)
        self.session.add_dht_router("dht.transmissionbt.com", 6881)
        self.session.add_dht_router("router.utorrent.com", 6881)
        
        logger.info("Torrent session configured")
    
    def create_torrent(self, file_path, trackers=None):
        """
        Create a torrent file from the given file.
        
        Args:
            file_path: Path to the file to create a torrent from
            trackers: Optional list of tracker URLs
            
        Returns:
            Path to the created .torrent file
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Creating torrent for: {file_path}")
        
        # Create torrent info
        fs = lt.file_storage()
        lt.add_files(fs, str(file_path))
        
        t = lt.create_torrent(fs)
        
        # Add trackers
        if trackers:
            for tracker in trackers:
                t.add_tracker(tracker)
        
        # Set creator and comment
        t.set_creator("ProxyTorrent v1.0")
        t.set_comment(f"Created from {file_path.name}")
        
        # Generate pieces
        lt.set_piece_hashes(t, str(file_path.parent))
        
        # Generate torrent file
        torrent_data = lt.bencode(t.generate())
        info_hash = hashlib.sha1(lt.bencode(t.generate_dict()[b'info'])).hexdigest()
        
        torrent_filename = f"{file_path.stem}_{info_hash[:8]}.torrent"
        torrent_path = TORRENT_DIR / torrent_filename
        
        with open(torrent_path, 'wb') as f:
            f.write(torrent_data)
        
        logger.info(f"Torrent created: {torrent_path}")
        logger.info(f"Info hash: {info_hash}")
        
        return torrent_path, info_hash
    
    def seed_torrent(self, torrent_path, file_path):
        """
        Start seeding a torrent.
        
        Args:
            torrent_path: Path to the .torrent file
            file_path: Path to the file being seeded
            
        Returns:
            Info hash of the torrent
        """
        file_path = Path(file_path)
        torrent_path = Path(torrent_path)
        
        logger.info(f"Starting to seed: {torrent_path}")
        
        # Add torrent to session
        params = {
            'ti': lt.torrent_info(str(torrent_path)),
            'save_path': str(file_path.parent),
        }
        
        handle = self.session.add_torrent(params)
        info_hash = str(handle.info_hash())
        
        self.active_torrents[info_hash] = {
            'handle': handle,
            'start_time': time.time(),
            'file_path': file_path,
            'torrent_path': torrent_path
        }
        
        logger.info(f"Seeding started for info hash: {info_hash}")
        
        return info_hash
    
    def get_torrent_status(self, info_hash):
        """Get status of a seeding torrent."""
        if info_hash not in self.active_torrents:
            return None
        
        handle = self.active_torrents[info_hash]['handle']
        status = handle.status()
        
        return {
            'info_hash': info_hash,
            'state': str(status.state),
            'progress': status.progress,
            'upload_rate': status.upload_rate,
            'download_rate': status.download_rate,
            'num_peers': status.num_peers,
            'num_seeds': status.num_seeds,
            'total_upload': status.total_upload,
            'total_download': status.total_download,
        }
    
    def stop_seeding(self, info_hash):
        """Stop seeding a torrent."""
        if info_hash in self.active_torrents:
            handle = self.active_torrents[info_hash]['handle']
            self.session.remove_torrent(handle)
            del self.active_torrents[info_hash]
            logger.info(f"Stopped seeding: {info_hash}")
    
    def cleanup_old_torrents(self):
        """Remove torrents that have been seeding for longer than configured time."""
        current_time = time.time()
        max_seed_time = SEED_TIME_HOURS * 3600
        
        to_remove = []
        for info_hash, torrent_info in self.active_torrents.items():
            if current_time - torrent_info['start_time'] > max_seed_time:
                to_remove.append(info_hash)
        
        for info_hash in to_remove:
            self.stop_seeding(info_hash)
            logger.info(f"Removed old torrent: {info_hash}")
