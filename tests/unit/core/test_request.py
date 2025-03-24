# ~/ClientFactory/tests/unit/test_request.py
"""
Tests for the core.request module
"""
import pytest
from unittest.mock import MagicMock

from clientfactory.core.request import (
    Request, RequestMethod, RequestConfig,
    RequestError, ValidationError
)


def test_request_initialization():
    """Test request initialization with different configurations"""
    # Basic initialization
    req = Request(
        method=RequestMethod.GET,
        url="https://api.example.com/test"
    )
    assert req.method == RequestMethod.GET
    assert req.url == "https://api.example.com/test"
    assert isinstance(req.config, RequestConfig)

    # Full initialization
    config = RequestConfig(timeout=60.0, maxretries=5)
    req = Request(
        method=RequestMethod.POST,
        url="https://api.example.com/test",
        params={"param1": "value1"},
        headers={"Content-Type": "application/json"},
        cookies={"session": "abc123"},
        json={"key": "value"},
        config=config
    )
    assert req.method == RequestMethod.POST
    assert req.params == {"param1": "value1"}
    assert req.headers == {"Content-Type": "application/json"}
    assert req.cookies == {"session": "abc123"}
    assert req.json == {"key": "value"}
    assert req.config.timeout == 60.0
    assert req.config.maxretries == 5


def test_request_method_conversion():
    """Test method string conversion to enum"""
    # String to enum conversion
    req = Request(
        method="get",
        url="https://api.example.com/test"
    )
    assert req.method == RequestMethod.GET

    req = Request(
        method="POST",
        url="https://api.example.com/test"
    )
    assert req.method == RequestMethod.POST

    # Invalid method
    with pytest.raises(ValidationError):
        Request(
            method="INVALID",
            url="https://api.example.com/test"
        )


def test_request_validation():
    """Test request validation rules"""
    # Missing URL
    with pytest.raises(ValidationError):
        Request(
            method=RequestMethod.GET,
            url=""
        )

    # GET request with body
    with pytest.raises(ValidationError):
        Request(
            method=RequestMethod.GET,
            url="https://api.example.com/test",
            json={"key": "value"}
        )

    # Both data and json specified
    with pytest.raises(ValidationError):
        Request(
            method=RequestMethod.POST,
            url="https://api.example.com/test",
            data={"key1": "value1"},
            json={"key2": "value2"}
        )


def test_request_prepare():
    """Test request preparation"""
    # Create a request
    req = Request(
        method=RequestMethod.POST,
        url="https://api.example.com/test",
        json={"key": "value"}
    )

    # Prepare the request
    prepared = req.prepare()

    # Check that prepared is a copy
    assert prepared is not req
    assert prepared.prepared

    # Check content-type header was added
    assert "Content-Type" in prepared.headers
    assert prepared.headers["Content-Type"] == "application/json"

    # Prepare an already prepared request
    prepared2 = prepared.prepare()
    assert prepared2 is prepared


def test_request_clone():
    """Test request cloning with updates"""
    # Create a request
    req = Request(
        method=RequestMethod.GET,
        url="https://api.example.com/test",
        params={"param1": "value1"},
        headers={"Accept": "application/json"},
        config=RequestConfig(timeout=30.0)
    )

    # Clone with updates
    clone = req.clone(
        params={"param2": "value2"},
        headers={"Authorization": "Bearer token"}
    )

    # Check original is unchanged
    assert req.params == {"param1": "value1"}
    assert req.headers == {"Accept": "application/json"}

    # Check clone has updates
    assert clone.params == {"param2": "value2"}
    assert clone.headers == {"Authorization": "Bearer token"}
    assert clone.method == req.method
    assert clone.url == req.url

    # Clone with config updates
    clone = req.clone(
        config={"timeout": 60.0, "maxretries": 5}
    )
    assert clone.config.timeout == 60.0
    assert clone.config.maxretries == 5

    # Clone with invalid config
    with pytest.raises(ValidationError):
        req.clone(config="invalid")


def test_request_factory():
    """Test RequestFactory functionality"""
    from clientfactory.core.request import RequestFactory

    # Create factory
    factory = RequestFactory(
        baseurl="https://api.example.com",
        defaultconfig=RequestConfig(timeout=60.0)
    )

    # Create request with factory
    req = factory.get("users")
    assert req.method == RequestMethod.GET
    assert req.url == "https://api.example.com/users"
    assert req.config.timeout == 60.0

    # Test other factory methods
    req = factory.post("users", json={"name": "test"})
    assert req.method == RequestMethod.POST
    assert req.json == {"name": "test"}

    req = factory.put("users/123", json={"name": "updated"})
    assert req.method == RequestMethod.PUT
    assert req.url == "https://api.example.com/users/123"

    req = factory.patch("users/123", json={"status": "active"})
    assert req.method == RequestMethod.PATCH

    req = factory.delete("users/123")
    assert req.method == RequestMethod.DELETE
