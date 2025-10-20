#!/usr/bin/env python3
"""
Unit tests for ProxyTorrent modules (no network required).
"""

import os
import sys
import tempfile
from pathlib import Path

# Test imports
print("Testing module imports...")
try:
    import config
    print("✓ config module imported")
    
    from fetcher import ContentFetcher
    print("✓ fetcher module imported")
    
    from torrent_manager import TorrentManager
    print("✓ torrent_manager module imported")
    
    from server import ProxyTorrentService
    print("✓ server module imported")
    
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test configuration
print("\nTesting configuration...")
try:
    assert hasattr(config, 'HOST'), "Missing HOST config"
    assert hasattr(config, 'PORT'), "Missing PORT config"
    assert hasattr(config, 'DOWNLOAD_DIR'), "Missing DOWNLOAD_DIR config"
    assert hasattr(config, 'TORRENT_DIR'), "Missing TORRENT_DIR config"
    print(f"✓ Configuration loaded: {config.HOST}:{config.PORT}")
except Exception as e:
    print(f"✗ Config test failed: {e}")
    sys.exit(1)

# Test torrent creation (without actual file)
print("\nTesting TorrentManager initialization...")
try:
    tm = TorrentManager()
    assert tm.session is not None, "Session not initialized"
    assert isinstance(tm.active_torrents, dict), "active_torrents not a dict"
    print("✓ TorrentManager initialized successfully")
except Exception as e:
    print(f"✗ TorrentManager test failed: {e}")
    sys.exit(1)

# Test torrent creation with a real file
print("\nTesting torrent creation...")
try:
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test content for torrent creation\n" * 100)
        test_file = f.name
    
    # Create torrent
    tm = TorrentManager()
    torrent_path, info_hash = tm.create_torrent(test_file)
    
    assert Path(torrent_path).exists(), "Torrent file not created"
    assert len(info_hash) == 40, f"Invalid info hash length: {len(info_hash)}"
    print(f"✓ Torrent created successfully: {info_hash[:8]}...")
    
    # Cleanup
    os.unlink(test_file)
    os.unlink(torrent_path)
    
except Exception as e:
    print(f"✗ Torrent creation test failed: {e}")
    sys.exit(1)

# Test ContentFetcher initialization
print("\nTesting ContentFetcher initialization...")
try:
    fetcher = ContentFetcher()
    assert fetcher.session is not None, "Session not initialized"
    print("✓ ContentFetcher initialized successfully")
except Exception as e:
    print(f"✗ ContentFetcher test failed: {e}")
    sys.exit(1)

# Test ProxyTorrentService initialization
print("\nTesting ProxyTorrentService initialization...")
try:
    service = ProxyTorrentService()
    assert service.fetcher is not None, "Fetcher not initialized"
    assert service.torrent_manager is not None, "TorrentManager not initialized"
    assert service.app is not None, "App not initialized"
    print("✓ ProxyTorrentService initialized successfully")
except Exception as e:
    print(f"✗ ProxyTorrentService test failed: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("ALL UNIT TESTS PASSED!")
print("="*50)
sys.exit(0)
