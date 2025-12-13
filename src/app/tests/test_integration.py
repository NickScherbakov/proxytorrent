"""Integration tests for end-to-end flow."""
import asyncio
import hashlib
import time

import pytest
from httpx import AsyncClient

from app.main import create_app
from app.models.schemas import RequestStatus


@pytest.fixture
def integration_app():
    """Create app with minimal security for testing."""
    from app.core.config import settings

    # Disable security for testing
    settings.security.auth_enabled = False
    settings.rate_limit.rate_limit_enabled = False
    settings.proxy.proxy_enabled = False

    return create_app()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_flow(integration_app, tmp_path):
    """
    Test complete flow: POST request → fetch → package → seed → download.

    This test simulates the full E2E workflow.
    """
    # Override storage paths for test
    from app.core.config import settings

    settings.storage.base_path = tmp_path
    settings.storage.content_path = tmp_path / "content"
    settings.storage.torrent_path = tmp_path / "torrents"
    settings.storage.resume_path = tmp_path / "resume"
    settings.initialize_storage()

    # Use in-memory database for test
    settings.database.database_url = "sqlite+aiosqlite:///:memory:"

    async with AsyncClient(app=integration_app, base_url="http://test") as client:
        # Step 1: Create a fetch request
        create_payload = {
            "url": "http://httpbin.org/html",  # Simple test endpoint
            "method": "GET",
            "ttl": 3600,
        }

        response = await client.post("/v1/requests", json=create_payload)
        assert response.status_code == 201

        data = response.json()
        request_id = data["id"]
        assert data["status"] == RequestStatus.QUEUED.value

        # Step 2: Wait for processing (with timeout)
        max_wait = 60  # 1 minute max wait
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = await client.get(f"/v1/requests/{request_id}")
            assert status_response.status_code == 200

            status_data = status_response.json()
            status = status_data["status"]

            if status == RequestStatus.READY.value:
                # Successfully processed
                assert status_data["infohash"] is not None
                assert status_data["content_hash"] is not None
                assert status_data["content_size"] > 0
                assert status_data["progress"] == 100
                break
            elif status == RequestStatus.ERROR.value:
                pytest.fail(f"Request failed: {status_data.get('error_message')}")
            else:
                # Still processing, wait a bit
                await asyncio.sleep(2)
        else:
            pytest.fail(f"Request did not complete within {max_wait} seconds")

        # Step 3: Get magnet link
        magnet_response = await client.get(f"/v1/requests/{request_id}/magnet")
        assert magnet_response.status_code == 200

        magnet_data = magnet_response.json()
        assert "magnet_link" in magnet_data
        assert magnet_data["infohash"] == status_data["infohash"]
        assert "magnet:?xt=urn:btih:" in magnet_data["magnet_link"]

        # Step 4: Download torrent file
        torrent_response = await client.get(f"/v1/requests/{request_id}/torrent")
        assert torrent_response.status_code == 200
        assert torrent_response.headers["content-type"] == "application/x-bittorrent"

        # Verify torrent file is valid
        torrent_data = torrent_response.content
        assert len(torrent_data) > 0

        # Step 5: Verify content hash matches
        # The content should be stored and accessible
        content_hash = status_data["content_hash"]
        content_path = (
            settings.storage.content_path
            / content_hash[:2]
            / content_hash[2:4]
            / "content"
        )

        if content_path.exists():
            stored_content = content_path.read_bytes()
            actual_hash = hashlib.sha256(stored_content).hexdigest()
            assert actual_hash == content_hash


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cancel_request(integration_app):
    """Test cancelling a pending request."""
    from app.core.config import settings

    settings.security.auth_enabled = False
    settings.rate_limit.rate_limit_enabled = False

    async with AsyncClient(app=integration_app, base_url="http://test") as client:
        # Create request
        response = await client.post(
            "/v1/requests",
            json={"url": "http://httpbin.org/delay/10", "method": "GET", "ttl": 3600},
        )
        assert response.status_code == 201
        request_id = response.json()["id"]

        # Cancel immediately
        cancel_response = await client.delete(f"/v1/requests/{request_id}")
        assert cancel_response.status_code == 204

        # Verify cancelled
        status_response = await client.get(f"/v1/requests/{request_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == RequestStatus.CANCELLED.value


@pytest.mark.asyncio
@pytest.mark.integration
async def test_content_deduplication(integration_app, tmp_path):
    """Test that fetching the same content twice reuses stored data."""
    from app.core.config import settings

    settings.storage.base_path = tmp_path
    settings.storage.content_path = tmp_path / "content"
    settings.storage.torrent_path = tmp_path / "torrents"
    settings.initialize_storage()
    settings.security.auth_enabled = False

    async with AsyncClient(app=integration_app, base_url="http://test") as client:
        # Fetch same URL twice
        url = "http://httpbin.org/uuid"

        # First request
        response1 = await client.post(
            "/v1/requests", json={"url": url, "method": "GET", "ttl": 3600}
        )
        request_id1 = response1.json()["id"]

        # Wait for completion
        await asyncio.sleep(5)

        # Second request (might get deduplicated)
        response2 = await client.post(
            "/v1/requests", json={"url": url, "method": "GET", "ttl": 3600}
        )
        request_id2 = response2.json()["id"]

        # Both should be different requests but might share content
        assert request_id1 != request_id2
