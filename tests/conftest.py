# ~/ClientFactory/tests/conftest.py
"""
Shared pytest fixtures for ClientFactory tests
"""
import pytest
from unittest.mock import MagicMock
from loguru import logger

from clientfactory.core.request import Request, RequestMethod, RequestConfig
from clientfactory.core.response import Response
from clientfactory.core.session import Session
from clientfactory.declarative.base import DeclarativeComponent

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for all tests"""
    logger.remove()  # Remove default handler
    logger.add(
        "tests/test.log",  # Log to file
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    # Optional: Also log to stderr for immediate visibility
    logger.add(
        lambda msg: print(msg, end=""),  # Print to console
        level="DEBUG",
        format="{level} | {message}"
    )

@pytest.fixture
def mock_session():
    """Create a mock session for testing"""
    session = MagicMock(spec=Session)
    # Configure the mock to return a simple response
    session.send.return_value = MagicMock(
        statuscode=200,
        rawcontent=b'{"success": true}',
        text='{"success": true}',
        json=lambda: {"success": True},
        ok=True
    )
    return session


@pytest.fixture
def mock_request():
    """Create a mock request for testing"""
    return Request(
        method=RequestMethod.GET,
        url="https://api.example.com/test",
        params={"param1": "value1"},
        headers={"Accept": "application/json"},
        config=RequestConfig(timeout=30.0)
    )


@pytest.fixture
def mock_response(mock_request):
    """Create a mock response for testing"""
    return Response(
        statuscode=200,
        headers={"Content-Type": "application/json"},
        rawcontent=b'{"success": true, "data": {"id": 123, "name": "Test"}}',
        request=mock_request
    )


@pytest.fixture(autouse=True)
def reset_component_metadata():
    """Reset DeclarativeComponent metadata between tests"""
    # Store original metadata
    original = DeclarativeComponent.__metadata__.copy()
    # Reset to empty
    DeclarativeComponent.__metadata__ = {}
    yield
    # Restore original metadata after test
    DeclarativeComponent.__metadata__ = original
