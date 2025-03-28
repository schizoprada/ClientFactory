# ~/ClientFactory/tests/unit/auth/test_token.py
"""
Unit tests for the TokenAuth class
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from clientfactory.auth.tokens import TokenAuth, TokenScheme, TokenError
from clientfactory.core import Request, RequestMethod


def test_init():
    """Test initialization"""
    # With default scheme
    auth = TokenAuth("test-token")
    assert auth.token == "test-token"
    assert auth.scheme == TokenScheme.BEARER
    assert auth.state.authenticated
    assert auth.state.token == "test-token"

    # With custom scheme
    auth = TokenAuth("test-token", TokenScheme.JWT)
    assert auth.scheme == TokenScheme.JWT


def test_init_with_string_scheme():
    """Test initialization with string scheme"""
    auth = TokenAuth("test-token", "Bearer")
    assert auth.scheme == TokenScheme.BEARER

    auth = TokenAuth("test-token", "JWT")
    assert auth.scheme == TokenScheme.JWT


def test_init_with_invalid_scheme():
    """Test initialization with invalid scheme raises error"""
    with pytest.raises(TokenError):
        TokenAuth("test-token", "InvalidScheme")


def test_authenticate():
    """Test authentication"""
    # Valid token
    auth = TokenAuth("test-token")
    assert auth.authenticate()
    assert auth.state.authenticated

    # Empty token
    auth = TokenAuth("")
    with pytest.raises(TokenError):
        auth.authenticate()


def test_prepare():
    """Test request preparation"""
    auth = TokenAuth("test-token")

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request
    prepared = auth.prepare(request)

    # Check that Authorization header was added
    assert "Authorization" in prepared.headers
    assert prepared.headers["Authorization"] == "Bearer test-token"


def test_prepare_with_different_schemes():
    """Test request preparation with different token schemes"""
    schemes = [
        (TokenScheme.BEARER, "Bearer test-token"),
        (TokenScheme.TOKEN, "Token test-token"),
        (TokenScheme.JWT, "JWT test-token"),
        (TokenScheme.MAC, "MAC test-token"),
        (TokenScheme.HAWK, "Hawk test-token"),
        (TokenScheme.CUSTOM, "Custom test-token"),
    ]

    for scheme, expected in schemes:
        auth = TokenAuth("test-token", scheme)
        request = Request(method=RequestMethod.GET, url="https://api.example.com/test")
        prepared = auth.prepare(request)

        assert prepared.headers["Authorization"] == expected


def test_update_token():
    """Test updating the token"""
    auth = TokenAuth("test-token")

    # Update token
    auth.updatetoken("new-token")

    # Check that token was updated
    assert auth.token == "new-token"
    assert auth.state.token == "new-token"
    assert auth.state.authenticated

    # Check that the new token is used in requests
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")
    prepared = auth.prepare(request)
    assert prepared.headers["Authorization"] == "Bearer new-token"


def test_update_token_with_expiration():
    """Test updating the token with an expiration time"""
    auth = TokenAuth("test-token")

    # Update token with expiration
    with patch('clientfactory.auth.tokens.datetime') as mock_datetime:
        mock_now = datetime(2020, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        auth.updatetoken("new-token", 3600)  # 1 hour

        # Check that expiration was set
        expected_expiry = mock_now + timedelta(seconds=3600)
        assert auth.state.expires == expected_expiry


def test_class_methods():
    """Test the class methods for creating different token types"""
    # Test Bearer token
    auth = TokenAuth.Bearer("test-token")
    assert auth.scheme == TokenScheme.BEARER

    # Test JWT token
    auth = TokenAuth.JWT("test-token")
    assert auth.scheme == TokenScheme.JWT

    # Test other token types
    assert TokenAuth.Token("test-token").scheme == TokenScheme.TOKEN
    assert TokenAuth.MAC("test-token").scheme == TokenScheme.MAC
    assert TokenAuth.Hawk("test-token").scheme == TokenScheme.HAWK
    assert TokenAuth.Custom("test-token").scheme == TokenScheme.CUSTOM
