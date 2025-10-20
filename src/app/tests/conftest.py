"""Test configuration and fixtures."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


@pytest.fixture
def app():
    """Create test app."""
    # Disable auth for tests
    settings.security.auth_enabled = False
    settings.rate_limit.rate_limit_enabled = False
    
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_fetcher(mocker):
    """Mock fetcher for tests."""
    from app.services.fetcher import FetchResult
    
    mock_result = FetchResult(
        content=b"test content",
        content_type="text/plain",
        status_code=200,
        headers={"content-type": "text/plain"},
        url="http://example.com",
    )
    
    mock = mocker.patch("app.services.fetcher.Fetcher.fetch")
    mock.return_value = mock_result
    return mock
