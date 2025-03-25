# ~/ClientFactory/tests/unit/client/test_declarative.py
import pytest
from clientfactory import clientclass, Client, searchresource, resource

def test_client_decorator_basic():
    """Test basic client decorator usage"""
    @clientclass
    class TestClient:
        baseurl = "https://api.test.com"

    assert issubclass(TestClient, Client)
    assert TestClient.baseurl == "https://api.test.com"
    assert TestClient.getbaseurl() == "https://api.test.com"

def test_client_decorator_with_baseurl():
    """Test client decorator with baseurl parameter"""
    @clientclass(baseurl="https://api.example.com")
    class TestClient:
        pass

    assert issubclass(TestClient, Client)
    assert TestClient.baseurl == "https://api.example.com"
    assert TestClient.getbaseurl() == "https://api.example.com"

def test_client_decorator_with_resources():
    """Test client decorator with nested resources"""
    @clientclass
    class TestClient:
        baseurl = "https://api.test.com"

        @resource
        class Users:
            path = "users"

        @searchresource
        class Search:
            path = "search"

    client = TestClient()
    assert hasattr(client, 'users')
    assert hasattr(client, 'search')

def test_client_decorator_inheritance():
    """Test client decorator with inheritance"""
    class BaseClient:
        baseurl = "https://api.base.com"

    @clientclass
    class TestClient(BaseClient):
        pass

    assert TestClient.baseurl == "https://api.base.com"

def test_client_decorator_instance():
    """Test instantiation of decorated client"""
    @clientclass
    class TestClient:
        baseurl = "https://api.test.com"

    instance = TestClient()
    assert isinstance(instance, Client)
    assert instance.baseurl == "https://api.test.com"
