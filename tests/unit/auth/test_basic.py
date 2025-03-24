# ~/ClientFactory/tests/unit/auth/test_basic.py
"""
Unit tests for the BasicAuth class
"""
import pytest
import base64
from unittest.mock import MagicMock

from clientfactory.auth.basic import BasicAuth, AuthError
from clientfactory.core import Request, RequestMethod


def test_init():
    """Test initialization"""
    auth = BasicAuth("user", "pass")
    assert auth.username == "user"
    assert auth.password == "pass"
    assert not auth.state.authenticated


def test_authenticate():
    """Test authentication"""
    # Valid credentials
    auth = BasicAuth("user", "pass")
    assert auth.authenticate()
    assert auth.state.authenticated

    # Empty credentials
    auth = BasicAuth("", "")
    with pytest.raises(AuthError):
        auth.authenticate()


def test_prepare():
    """Test request preparation"""
    auth = BasicAuth("user", "pass")

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request
    prepared = auth.prepare(request)

    # Check that Authorization header was added
    assert "Authorization" in prepared.headers

    # Check that the header value is correctly formatted
    expected = f"Basic {base64.b64encode(b'user:pass').decode('utf-8')}"
    assert prepared.headers["Authorization"] == expected


def test_from_url():
    """Test creation from URL with embedded credentials"""
    # URL with credentials
    auth = BasicAuth.FromURL("https://user:pass@api.example.com")
    assert auth.username == "user"
    assert auth.password == "pass"

    # URL without credentials
    with pytest.raises(AuthError):
        BasicAuth.FromURL("https://api.example.com")


def test_prepare_without_auth():
    """Test that preparing a request without authenticating first works"""
    auth = BasicAuth("user", "pass")

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request without explicitly authenticating
    prepared = auth.prepare(request)

    # Check that we're now authenticated
    assert auth.state.authenticated

    # Check that Authorization header was added
    assert "Authorization" in prepared.headers


def test_invalid_credentials_raise_error():
    """Test that invalid credentials raise error on authentication"""
    # No username
    auth = BasicAuth("", "pass")
    with pytest.raises(AuthError):
        auth.prepare(Request(method=RequestMethod.GET, url="https://api.example.com/test"))

    # No password
    auth = BasicAuth("user", "")
    with pytest.raises(AuthError):
        auth.prepare(Request(method=RequestMethod.GET, url="https://api.example.com/test"))
