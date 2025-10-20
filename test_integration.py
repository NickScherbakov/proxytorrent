#!/usr/bin/env python3
"""
Simple integration test for ProxyTorrent service.
"""

import os
import time
import requests
import subprocess
import signal
import sys

def test_service():
    """Test the ProxyTorrent service."""
    print("Starting ProxyTorrent server...")
    
    # Start the server
    server_process = subprocess.Popen(
        [sys.executable, "server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        # Test 1: Health check
        print("\n[TEST 1] Health check...")
        response = requests.get("http://localhost:8080/health", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data['status'] == 'healthy', f"Service not healthy: {data}"
        print("✓ Health check passed")
        
        # Test 2: Fetch a small test file
        print("\n[TEST 2] Fetching content...")
        response = requests.post(
            "http://localhost:8080/fetch",
            json={
                "url": "https://httpbin.org/robots.txt",
                "filename": "test_robots.txt"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Fetch failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data['success'] == True, f"Fetch not successful: {data}"
        assert 'info_hash' in data, "No info_hash in response"
        print(f"✓ Fetch passed. Info hash: {data['info_hash']}")
        
        info_hash = data['info_hash']
        
        # Test 3: Check status
        print("\n[TEST 3] Checking torrent status...")
        time.sleep(2)
        response = requests.get(f"http://localhost:8080/status/{info_hash}", timeout=5)
        assert response.status_code == 200, f"Status check failed: {response.status_code}"
        status = response.json()
        assert 'info_hash' in status, "No info_hash in status"
        assert status['info_hash'] == info_hash, "Info hash mismatch"
        print(f"✓ Status check passed. State: {status['state']}, Peers: {status['num_peers']}")
        
        # Test 4: Download torrent file
        print("\n[TEST 4] Downloading torrent file...")
        torrent_filename = data['torrent_file'].split('/')[-1]
        response = requests.get(f"http://localhost:8080/torrents/{torrent_filename}", timeout=5)
        assert response.status_code == 200, f"Torrent download failed: {response.status_code}"
        assert len(response.content) > 0, "Empty torrent file"
        print(f"✓ Torrent download passed. Size: {len(response.content)} bytes")
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED!")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        server_process.send_signal(signal.SIGTERM)
        time.sleep(1)
        if server_process.poll() is None:
            server_process.kill()
        print("Server stopped")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = test_service()
    sys.exit(0 if success else 1)
