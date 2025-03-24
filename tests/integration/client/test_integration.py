# ~/ClientFactory/tests/integration/client/test_integration.py
import pytest
import sys
from unittest.mock import patch, call, ANY, Mock
import json
import requests
from loguru import logger as log

# Configure logging for tests
log.remove()  # Remove default handler
log.configure(handlers=[{"sink": sys.stdout, "level": "DEBUG"}])

from clientfactory.client import Client, ClientBuilder
from clientfactory.core import Resource, ResourceConfig
from clientfactory.core.request import RequestMethod
from clientfactory.core.resource import MethodConfig


# Create a simple resource for testing with JSONPlaceholder API
class TodoResource:
    """Resource for the JSONPlaceholder todos API"""
    path = "todos"  # Explicitly define the path

    # Add the _resourceconfig attribute that the Client.register() method expects
    _resourceconfig = ResourceConfig(
        name="Todos",
        path="todos"
    )

    # Add the method configs to the resource config
    _resourceconfig.methods["list"] = MethodConfig(
        name="list",
        method=RequestMethod.GET
    )

    _resourceconfig.methods["get"] = MethodConfig(
        name="get",
        method=RequestMethod.GET,
        path="{id}"
    )

    _resourceconfig.methods["create"] = MethodConfig(
        name="create",
        method=RequestMethod.POST
    )


# Test with mocked HTTP responses
class TestClientIntegration:
    """Integration tests for Client with mocked HTTP responses"""

    @pytest.fixture
    def mock_response(self):
        """Create a mock response"""
        class MockResponse:
            def __init__(self, json_data, status_code=200, headers=None):
                self.json_data = json_data
                self.status_code = status_code
                self.headers = headers or {}
                self.content = json.dumps(json_data).encode()

            def json(self):
                return self.json_data

        return MockResponse

    @pytest.fixture
    def client(self):
        """Create a test client"""
        log.info("Creating test client with baseurl: https://jsonplaceholder.typicode.com")
        client = ClientBuilder().baseurl("https://jsonplaceholder.typicode.com").build()
        log.info(f"Client created with baseurl: {client.baseurl}")
        return client

    def test_client_builder_url_assignment(self, client):
        log.info(f"Testing client baseurl: {client.baseurl}")
        assert client.baseurl == "https://jsonplaceholder.typicode.com"
        log.info("Client baseurl test passed")

    def test_resource_registration(self, client):
        """Test manual resource registration"""
        log.info("Registering TodoResource with client")
        client.register(TodoResource)
        log.info("Checking if resource was registered correctly")
        assert hasattr(client, "todoresource")
        assert client._resources["todoresource"]._config.path == "todos"
        log.info("Resource was registered correctly")

        # Additional check to debug parent chain
        log.info(f"Resource parent: {client._resources['todoresource']._config.parent}")
        log.info(f"Parent has baseurl? {hasattr(client._resources['todoresource']._config.parent, 'baseurl')}")
        if hasattr(client._resources['todoresource']._config.parent, 'baseurl'):
            log.info(f"Parent baseurl: {client._resources['todoresource']._config.parent.baseurl}")

    @patch('requests.Session.send')
    def test_list_todos(self, mock_send, mock_response, client):
        """Test listing todos"""
        # Setup mock response
        todos_data = [
            {"id": 1, "title": "Test Todo 1", "completed": False},
            {"id": 2, "title": "Test Todo 2", "completed": True}
        ]
        mock_send.return_value = mock_response(todos_data)

        # Register resource and make request
        log.info("Registering TodoResource for list_todos test")
        client.register(TodoResource)
        log.info("Calling todoresource.list()")
        response = client.todoresource.list()

        # Verify response
        log.info(f"Response status: {response.statuscode}, OK: {response.ok}")
        assert response.ok
        assert response.json() == todos_data

        # Verify request
        args, kwargs = mock_send.call_args
        prepared_request = args[0]
        log.info(f"Request method: {prepared_request.method}")
        log.info(f"Request URL: {prepared_request.url}")

        assert prepared_request.method == "GET"
        # Check that URL contains the base URL + 'todos' path
        assert "jsonplaceholder.typicode.com" in prepared_request.url
        assert "/todos" in prepared_request.url
        log.info("List todos test passed")

    @patch('requests.Session.send')
    def test_get_todo(self, mock_send, mock_response, client):
        """Test getting a specific todo"""
        # Setup mock response
        todo_data = {"id": 1, "title": "Test Todo", "completed": False}
        mock_send.return_value = mock_response(todo_data)

        # Register resource and make request
        log.info("Registering TodoResource for get_todo test")
        client.register(TodoResource)
        log.info("Calling todoresource.get(1)")
        response = client.todoresource.get(1)

        # Verify response
        log.info(f"Response status: {response.statuscode}, OK: {response.ok}")
        assert response.ok
        assert response.json() == todo_data

        # Verify request
        args, kwargs = mock_send.call_args
        prepared_request = args[0]
        log.info(f"Request method: {prepared_request.method}")
        log.info(f"Request URL: {prepared_request.url}")

        assert prepared_request.method == "GET"
        # Check that URL contains the base URL + 'todos' path + ID
        assert "jsonplaceholder.typicode.com" in prepared_request.url
        assert "/todos/1" in prepared_request.url
        log.info("Get todo test passed")

    @patch('requests.Session.send')
    def test_create_todo(self, mock_send, mock_response, client):
        """Test creating a todo"""
        # Setup mock response
        new_todo = {"title": "New Todo", "completed": False}
        created_todo = {"id": 201, **new_todo}
        mock_send.return_value = mock_response(created_todo, status_code=201)

        # Register resource and make request
        log.info("Registering TodoResource for create_todo test")
        client.register(TodoResource)
        log.info("Calling todoresource.create(json=new_todo)")
        response = client.todoresource.create(json=new_todo)

        # Verify response
        log.info(f"Response status: {response.statuscode}, OK: {response.ok}")
        assert response.ok
        assert response.json() == created_todo

        # Verify request
        args, kwargs = mock_send.call_args
        prepared_request = args[0]
        log.info(f"Request method: {prepared_request.method}")
        log.info(f"Request URL: {prepared_request.url}")
        log.info(f"Request headers: {prepared_request.headers}")

        assert prepared_request.method == "POST"
        # Check that URL contains the base URL + 'todos' path
        assert "jsonplaceholder.typicode.com" in prepared_request.url
        assert "/todos" in prepared_request.url
        assert "application/json" in prepared_request.headers.get("Content-Type", "")
        log.info("Create todo test passed")

    # Add a test to directly inspect request creation
    def test_direct_request_url_construction(self, client):
        """Test request URL construction directly"""
        log.info("Testing direct request URL construction")
        # Register resource
        client.register(TodoResource)
        resource = client._resources["todoresource"]

        # Get the method configuration for "list"
        method_config = resource._config.methods["list"]

        # Call _buildrequest directly to see what URL it produces
        log.info("Calling _buildrequest directly")
        request = resource._buildrequest(method_config)

        log.info(f"Request URL: {request.url}")
        assert request.url.startswith("https://")
        assert "jsonplaceholder.typicode.com" in request.url
        assert "/todos" in request.url
        log.info("Direct URL construction test passed")
