"""
Example client script demonstrating how to use the ProxyTorrent service.
"""

import requests
import time
import json

# Service URL
BASE_URL = "http://localhost:8080"


def fetch_and_seed(url, filename=None, trackers=None):
    """Request content to be fetched and seeded."""
    print(f"Requesting fetch for: {url}")
    
    payload = {"url": url}
    if filename:
        payload["filename"] = filename
    if trackers:
        payload["trackers"] = trackers
    
    response = requests.post(f"{BASE_URL}/fetch", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success! Info hash: {result['info_hash']}")
        print(f"Torrent file available at: {BASE_URL}{result['torrent_file']}")
        return result['info_hash']
    else:
        print(f"Error: {response.text}")
        return None


def check_status(info_hash):
    """Check the status of a torrent."""
    print(f"\nChecking status for: {info_hash}")
    
    response = requests.get(f"{BASE_URL}/status/{info_hash}")
    
    if response.status_code == 200:
        status = response.json()
        print(json.dumps(status, indent=2))
        return status
    else:
        print(f"Error: {response.text}")
        return None


def download_torrent(torrent_filename):
    """Download the .torrent file."""
    print(f"\nDownloading torrent file: {torrent_filename}")
    
    response = requests.get(f"{BASE_URL}/torrents/{torrent_filename}")
    
    if response.status_code == 200:
        output_path = f"/tmp/{torrent_filename}"
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"Torrent saved to: {output_path}")
        return output_path
    else:
        print(f"Error: {response.text}")
        return None


def main():
    """Example usage."""
    # Example 1: Fetch a small test file
    print("=== Example 1: Basic fetch ===")
    info_hash = fetch_and_seed(
        url="https://httpbin.org/robots.txt",
        filename="robots.txt"
    )
    
    if info_hash:
        # Wait a moment for seeding to start
        time.sleep(2)
        
        # Check status
        status = check_status(info_hash)
        
        if status:
            print(f"\nTorrent is {status['state']} with {status['num_peers']} peers")
    
    # Example 2: Fetch with trackers
    print("\n\n=== Example 2: Fetch with trackers ===")
    info_hash = fetch_and_seed(
        url="https://httpbin.org/json",
        filename="sample.json",
        trackers=[
            "udp://tracker.opentrackr.org:1337/announce",
            "udp://open.demonii.com:1337/announce"
        ]
    )
    
    if info_hash:
        time.sleep(2)
        check_status(info_hash)


if __name__ == "__main__":
    print("ProxyTorrent Client Example")
    print("=" * 50)
    print("\nMake sure the ProxyTorrent service is running on localhost:8080")
    print()
    
    try:
        # Check if service is running
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("Service is healthy!")
            print()
            main()
        else:
            print("Service responded but may not be healthy")
    except requests.exceptions.RequestException as e:
        print(f"Error: Cannot connect to ProxyTorrent service: {e}")
        print("Please start the service first with: python server.py")
