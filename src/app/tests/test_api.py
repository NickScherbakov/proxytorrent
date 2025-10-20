"""Tests for API endpoints."""
import pytest


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "uptime" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_create_request(client):
    """Test creating a fetch request."""
    payload = {
        "url": "http://example.com",
        "method": "GET",
        "ttl": 3600,
    }
    
    response = client.post("/v1/requests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "queued"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_request_status(client):
    """Test getting request status."""
    # First create a request
    payload = {
        "url": "http://example.com",
        "method": "GET",
        "ttl": 3600,
    }
    
    create_response = client.post("/v1/requests", json=payload)
    assert create_response.status_code == 201
    request_id = create_response.json()["id"]
    
    # Get status
    response = client.get(f"/v1/requests/{request_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == request_id
    assert "status" in data
    assert "url" in data


@pytest.mark.asyncio
async def test_get_nonexistent_request(client):
    """Test getting non-existent request."""
    response = client.get("/v1/requests/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_request(client):
    """Test cancelling a request."""
    # First create a request
    payload = {
        "url": "http://example.com",
        "method": "GET",
        "ttl": 3600,
    }
    
    create_response = client.post("/v1/requests", json=payload)
    assert create_response.status_code == 201
    request_id = create_response.json()["id"]
    
    # Cancel it
    response = client.delete(f"/v1/requests/{request_id}")
    assert response.status_code == 204
    
    # Verify status
    status_response = client.get(f"/v1/requests/{request_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "cancelled"
