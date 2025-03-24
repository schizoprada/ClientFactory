# ~/ClientFactory/tests/integration/decorators/test_decorators.py
"""
Integration tests for decorators
"""
import pytest
from unittest.mock import MagicMock, patch

from clientfactory.client import Client, ClientBuilder
from clientfactory.decorators import resource, get, post, put, delete, preprocess, postprocess
from clientfactory.core import Session, Request, Response, RequestMethod


def test_client_with_resource():
    """Test client with decorated resource class"""

    @resource
    class Users:
        @get("users")
        def list_users(self):
            pass

        @get("users/{id}")
        def get_user(self, id):
            pass

        @post("users")
        def create_user(self, **data):
            pass

        @put("users/{id}")
        def update_user(self, id, **data):
            pass

        @delete("users/{id}")
        def delete_user(self, id):
            pass

    # Create client with mock session
    client = ClientBuilder().baseurl("https://api.example.com").build()
    client._session = MagicMock(spec=Session)

    # Register the resource
    client.register(Users)

    # Verify resource was registered
    assert hasattr(client, 'users')
    assert 'users' in client._resources

    # Create mock response for testing
    mock_response = MagicMock(spec=Response)
    mock_response.statuscode = 200
    mock_response.json.return_value = {"id": 123, "name": "Test User"}
    client._session.send.return_value = mock_response

    # Test methods
    result = client.users.get_user(123)
    assert result == mock_response
    client._session.send.assert_called()


def test_resource_with_transforms():
    """Test resource with transform decorators"""

    def add_auth_header(request):
        return request.clone(headers={"Authorization": "Bearer test-token"})

    def extract_data(response):
        return response.json()["data"]

    @resource
    class Items:
        @get("items")
        @preprocess(add_auth_header)
        @postprocess(extract_data)
        def list_items(self):
            pass

    # Create client with mock session
    client = ClientBuilder().baseurl("https://api.example.com").build()
    client._session = MagicMock(spec=Session)

    # Register the resource
    client.register(Items)

    # Create mock request/response for checking transforms
    mock_request = Request(method=RequestMethod.GET, url="https://api.example.com/items")
    mock_response = MagicMock(spec=Response)
    mock_response.json.return_value = {"data": [{"id": 1, "name": "Item 1"}]}

    # Mock the session.send method to capture the request and return our response
    def mock_send(request):
        # Verify preprocessing was applied (auth header added)
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == "Bearer test-token"
        return mock_response

    client._session.send.side_effect = mock_send

    # Call the method
    result = client.items.list_items()

    # Verify postprocessing was applied (data extracted)
    assert result == [{"id": 1, "name": "Item 1"}]
    client._session.send.assert_called_once()


def test_nested_resources():
    """Test nested resources with decorators"""

    @resource
    class API:
        @resource
        class Users:
            @get("users")
            def list_users(self):
                pass

            @get("users/{id}")
            def get_user(self, id):
                pass

        @resource
        class Items:
            @get("items")
            def list_items(self):
                pass

    # Create client with the resource
    client = ClientBuilder().baseurl("https://api.example.com").build()
    client._session = MagicMock(spec=Session)
    client.register(API)

    # Verify resources were registered
    assert hasattr(client, 'api')
    assert hasattr(client.api, 'users')
    assert hasattr(client.api, 'items')

    # Create mock response
    mock_response = MagicMock(spec=Response)
    client._session.send.return_value = mock_response

    # Test nested resource methods
    result1 = client.api.users.list_users()
    result2 = client.api.items.list_items()

    assert result1 == mock_response
    assert result2 == mock_response
    assert client._session.send.call_count == 2
