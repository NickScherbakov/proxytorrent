#!/usr/bin/env python3
"""
Example client for ProxyTorrent API.

This script demonstrates how to:
1. Create a fetch request
2. Monitor its progress
3. Download the torrent file
4. Get the magnet link
"""
import argparse
import hashlib
import hmac
import json
import sys
import time

import requests


class ProxyTorrentClient:
    """Simple client for ProxyTorrent API."""

    def __init__(self, base_url: str, hmac_secret: str | None = None):
        """Initialize client."""
        self.base_url = base_url.rstrip("/")
        self.hmac_secret = hmac_secret

    def _sign_request(self, body: str) -> str:
        """Generate HMAC signature for request body."""
        if not self.hmac_secret:
            raise ValueError("HMAC secret required for signing")
        
        signature = hmac.new(
            self.hmac_secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def create_request(
        self, url: str, method: str = "GET", ttl: int = 3600
    ) -> dict:
        """Create a fetch request."""
        payload = {
            "url": url,
            "method": method,
            "ttl": ttl,
        }
        
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}
        
        if self.hmac_secret:
            signature = self._sign_request(body)
            headers["X-Signature"] = signature
        
        response = requests.post(
            f"{self.base_url}/v1/requests",
            data=body,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    def get_status(self, request_id: str) -> dict:
        """Get request status."""
        headers = {}
        if self.hmac_secret:
            # For GET requests, we don't have a body, but still need auth
            # Use empty body for signature
            signature = self._sign_request("")
            headers["X-Signature"] = signature
        
        response = requests.get(
            f"{self.base_url}/v1/requests/{request_id}",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    def get_magnet(self, request_id: str) -> dict:
        """Get magnet link."""
        headers = {}
        if self.hmac_secret:
            signature = self._sign_request("")
            headers["X-Signature"] = signature
        
        response = requests.get(
            f"{self.base_url}/v1/requests/{request_id}/magnet",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    def download_torrent(self, request_id: str, output_path: str) -> None:
        """Download torrent file."""
        headers = {}
        if self.hmac_secret:
            signature = self._sign_request("")
            headers["X-Signature"] = signature
        
        response = requests.get(
            f"{self.base_url}/v1/requests/{request_id}/torrent",
            headers=headers,
        )
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(response.content)

    def wait_for_completion(
        self, request_id: str, timeout: int = 300, interval: int = 2
    ) -> dict:
        """Wait for request to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_status(request_id)
            
            if status["status"] == "ready":
                return status
            elif status["status"] == "error":
                raise RuntimeError(f"Request failed: {status.get('error_message')}")
            
            print(f"Status: {status['status']} ({status['progress']}%)")
            time.sleep(interval)
        
        raise TimeoutError(f"Request did not complete within {timeout} seconds")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ProxyTorrent API client example")
    parser.add_argument(
        "--url",
        required=True,
        help="URL to fetch",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="ProxyTorrent API base URL",
    )
    parser.add_argument(
        "--hmac-secret",
        help="HMAC secret for authentication (if enabled)",
    )
    parser.add_argument(
        "--output",
        default="output.torrent",
        help="Output torrent file path",
    )
    parser.add_argument(
        "--method",
        default="GET",
        choices=["GET", "POST", "PUT", "DELETE", "PATCH"],
        help="HTTP method",
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=3600,
        help="Cache TTL in seconds",
    )
    
    args = parser.parse_args()
    
    # Create client
    client = ProxyTorrentClient(args.base_url, args.hmac_secret)
    
    try:
        # Step 1: Create request
        print(f"Creating fetch request for {args.url}...")
        result = client.create_request(args.url, args.method, args.ttl)
        request_id = result["id"]
        print(f"Request created: {request_id}")
        print(f"Status: {result['status']}")
        
        # Step 2: Wait for completion
        print("\nWaiting for completion...")
        status = client.wait_for_completion(request_id)
        
        print("\n✓ Request completed!")
        print(f"  Infohash: {status['infohash']}")
        print(f"  Content size: {status['content_size']} bytes")
        print(f"  Content type: {status['content_type']}")
        
        # Step 3: Get magnet link
        print("\nGetting magnet link...")
        magnet = client.get_magnet(request_id)
        print(f"  Magnet: {magnet['magnet_link']}")
        
        # Step 4: Download torrent file
        print(f"\nDownloading torrent to {args.output}...")
        client.download_torrent(request_id, args.output)
        print(f"✓ Torrent saved to {args.output}")
        
        print("\n✓ Done!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
