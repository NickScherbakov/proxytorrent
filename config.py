"""
ProxyTorrent - A combined Proxy + BitTorrent service.

This module provides the main configuration and utility functions.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8080'))

# Proxy Configuration
PROXY_HOST = os.getenv('PROXY_HOST', '')
PROXY_PORT = os.getenv('PROXY_PORT', '')
PROXY_TYPE = os.getenv('PROXY_TYPE', 'socks5')
PROXY_USERNAME = os.getenv('PROXY_USERNAME', '')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD', '')

# Storage Configuration
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', '/tmp/proxytorrent/downloads'))
TORRENT_DIR = Path(os.getenv('TORRENT_DIR', '/tmp/proxytorrent/torrents'))

# Seeding Configuration
SEED_TIME_HOURS = int(os.getenv('SEED_TIME_HOURS', '24'))
MAX_UPLOAD_RATE_KB = int(os.getenv('MAX_UPLOAD_RATE_KB', '0'))
MAX_DOWNLOAD_RATE_KB = int(os.getenv('MAX_DOWNLOAD_RATE_KB', '0'))

# Ensure directories exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
TORRENT_DIR.mkdir(parents=True, exist_ok=True)


def get_proxy_dict():
    """Get proxy configuration as a dictionary."""
    if not PROXY_HOST or not PROXY_PORT:
        return None
    
    proxy_url = f"{PROXY_TYPE}://"
    if PROXY_USERNAME and PROXY_PASSWORD:
        proxy_url += f"{PROXY_USERNAME}:{PROXY_PASSWORD}@"
    proxy_url += f"{PROXY_HOST}:{PROXY_PORT}"
    
    return {
        'http': proxy_url,
        'https': proxy_url
    }
