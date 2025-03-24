# ~/ClientFactory/tests/unit/auth/test_apikey.py
"""
Unit tests for the APIKeyAuth class
"""
import pytest
from unittest.mock import MagicMock

from clientfactory.auth.apikey import APIKeyAuth, KeyLocation, APIKeyError
from clientfactory.core import Request, RequestMethod


def test_init_with_string_location():
    """Test initialization with string location"""
    auth = APIKeyAuth("testkey", location="header")
    assert auth.location == KeyLocation.HEADER

    auth = APIKeyAuth("testkey", location="query")
    assert auth.location == KeyLocation.QUERY

    auth = APIKeyAuth("testkey", location="cookie")
    assert auth.location == KeyLocation.COOKIE


def test_init_with_invalid_location():
    """Test initialization with invalid location raises error"""
    with pytest.raises(APIKeyError):
        APIKeyAuth("testkey", location="invalid")


def test_header_location():
    """Test that API key is added to header"""
    # Create auth with header location
    auth = APIKeyAuth("testkey", name="X-API-Key", location=KeyLocation.HEADER)

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request
    prepared = auth.prepare(request)

    # Check that header was added
    assert "X-API-Key" in prepared.headers
    assert prepared.headers["X-API-Key"] == "testkey"


def test_query_location():
    """Test that API key is added to query parameters"""
    # Create auth with query location
    auth = APIKeyAuth("testkey", name="api_key", location=KeyLocation.QUERY)

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request
    prepared = auth.prepare(request)

    # Check that query param was added
    assert "api_key" in prepared.params
    assert prepared.params["api_key"] == "testkey"


def test_cookie_location():
    """Test that API key is added to cookies"""
    # Create auth with cookie location
    auth = APIKeyAuth("testkey", name="api_key", location=KeyLocation.COOKIE)

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request
    prepared = auth.prepare(request)

    # Check that cookie was added
    assert "api_key" in prepared.cookies
    assert prepared.cookies["api_key"] == "testkey"


def test_with_prefix():
    """Test that prefix is correctly added to the key"""
    # Create auth with prefix
    auth = APIKeyAuth("testkey", prefix="Bearer")

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request
    prepared = auth.prepare(request)

    # Check that prefix was added
    assert prepared.headers["X-API-Key"] == "Bearer testkey"


def test_class_methods():
    """Test the class methods for creating different auth types"""
    # Test Header
    auth = APIKeyAuth.Header("testkey", "X-Auth")
    assert auth.location == KeyLocation.HEADER
    assert auth.name == "X-Auth"

    # Test Query
    auth = APIKeyAuth.Query("testkey", "apikey")
    assert auth.location == KeyLocation.QUERY
    assert auth.name == "apikey"

    # Test Cookie
    auth = APIKeyAuth.Cookie("testkey", "session")
    assert auth.location == KeyLocation.COOKIE
    assert auth.name == "session"


def test_empty_key_raises_error():
    """Test that empty API key raises error on authentication"""
    auth = APIKeyAuth("")

    with pytest.raises(APIKeyError):
        auth.authenticate()
