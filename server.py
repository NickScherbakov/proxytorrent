"""
Main API server for ProxyTorrent service.
"""

import logging
import asyncio
from pathlib import Path
from aiohttp import web
import json

from fetcher import ContentFetcher
from torrent_manager import TorrentManager
from config import HOST, PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxyTorrentService:
    """Main service handling fetch and torrent operations."""
    
    def __init__(self):
        self.fetcher = ContentFetcher()
        self.torrent_manager = TorrentManager()
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes."""
        self.app.router.add_post('/fetch', self.handle_fetch)
        self.app.router.add_get('/status/{info_hash}', self.handle_status)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/torrents/{filename}', self.handle_download_torrent)
    
    async def handle_fetch(self, request):
        """
        Handle fetch request.
        
        Expected JSON body:
        {
            "url": "https://example.com/file.zip",
            "filename": "optional_custom_name.zip",
            "trackers": ["http://tracker1.com:8080/announce", ...]
        }
        """
        try:
            data = await request.json()
            url = data.get('url')
            filename = data.get('filename')
            trackers = data.get('trackers', [])
            
            if not url:
                return web.json_response(
                    {'error': 'URL is required'},
                    status=400
                )
            
            logger.info(f"Received fetch request for: {url}")
            
            # Fetch content
            file_path = await asyncio.get_event_loop().run_in_executor(
                None, self.fetcher.fetch, url, filename
            )
            
            # Create torrent
            torrent_path, info_hash = await asyncio.get_event_loop().run_in_executor(
                None, self.torrent_manager.create_torrent, file_path, trackers
            )
            
            # Start seeding
            await asyncio.get_event_loop().run_in_executor(
                None, self.torrent_manager.seed_torrent, torrent_path, file_path
            )
            
            return web.json_response({
                'success': True,
                'info_hash': info_hash,
                'torrent_file': f'/torrents/{Path(torrent_path).name}',
                'message': 'Content fetched and seeding started'
            })
            
        except Exception as e:
            logger.error(f"Error handling fetch request: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    async def handle_status(self, request):
        """Get status of a torrent by info hash."""
        info_hash = request.match_info['info_hash']
        
        status = await asyncio.get_event_loop().run_in_executor(
            None, self.torrent_manager.get_torrent_status, info_hash
        )
        
        if status is None:
            return web.json_response(
                {'error': 'Torrent not found'},
                status=404
            )
        
        return web.json_response(status)
    
    async def handle_health(self, request):
        """Health check endpoint."""
        return web.json_response({
            'status': 'healthy',
            'active_torrents': len(self.torrent_manager.active_torrents)
        })
    
    async def handle_download_torrent(self, request):
        """Download a torrent file."""
        filename = request.match_info['filename']
        from config import TORRENT_DIR
        
        torrent_path = TORRENT_DIR / filename
        
        if not torrent_path.exists():
            return web.json_response(
                {'error': 'Torrent file not found'},
                status=404
            )
        
        return web.FileResponse(torrent_path)
    
    async def cleanup_task(self):
        """Background task to cleanup old torrents."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await asyncio.get_event_loop().run_in_executor(
                    None, self.torrent_manager.cleanup_old_torrents
                )
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def start_background_tasks(self, app):
        """Start background tasks."""
        app['cleanup_task'] = asyncio.create_task(self.cleanup_task())
    
    async def cleanup_background_tasks(self, app):
        """Cleanup background tasks."""
        app['cleanup_task'].cancel()
        await app['cleanup_task']
    
    def run(self):
        """Start the service."""
        self.app.on_startup.append(self.start_background_tasks)
        self.app.on_cleanup.append(self.cleanup_background_tasks)
        
        logger.info(f"Starting ProxyTorrent service on {HOST}:{PORT}")
        web.run_app(self.app, host=HOST, port=PORT)


def main():
    """Main entry point."""
    service = ProxyTorrentService()
    service.run()


if __name__ == '__main__':
    main()
