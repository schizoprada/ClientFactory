# ~/ClientFactory/tests/unit/declarative/test_client.py
import pytest
from clientfactory.declarative.client import DeclarativeClient, client
from clientfactory.declarative.resource import DeclarativeResource, resource

def test_declarative_client_basic():
    """Test basic DeclarativeClient functionality"""
    class TestClient(DeclarativeClient):
        baseurl = "https://api.test.com"

        @resource
        class TestResource:
            pass

    assert TestClient.getmetadata('baseurl') == "https://api.test.com"
    assert 'testresource' in TestClient.getresources()

def test_client_decorator():
    """Test @client decorator"""
    @client(baseurl="https://api.test.com")
    class Test:
        @resource
        class TestResource:
            path = "/test"

    assert issubclass(Test, DeclarativeClient)
    assert Test.getbaseurl() == "https://api.test.com"
    assert 'testresource' in Test.getresources()

def test_client_resource_registration():
    """Test automatic resource registration"""
    @resource(name="myresource")  # Explicitly name it
    class TestResource(DeclarativeResource):
        path = "/test"

    @client
    class TestClient:
        resource = TestResource

    resources = TestClient.getresources()
    assert "myresource" in resources  # Test with explicit name
    assert resources["myresource"] == TestResource  # Check the actual registered resource

def test_client_inheritance():
    """Test client inheritance behavior"""
    class BaseClient(DeclarativeClient):
        baseurl = "https://api.base.com"

        @resource
        class BaseResource:
            path = "/base"

    class ChildClient(BaseClient):
        @resource
        class ChildResource:
            path = "/child"

    assert 'baseresource' in ChildClient.getresources()
    assert 'childresource' in ChildClient.getresources()
