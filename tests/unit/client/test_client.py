# ~/ClientFactory/tests/unit/client/test_client.py
import pytest
from unittest.mock import MagicMock, patch

from clientfactory.client import Client, ClientConfig, ClientError
from clientfactory.core import Resource, ResourceConfig


class TestClient:
    """Tests for the Client class"""

    def test_init_with_defaults(self):
        """Test initializing a client with default values"""
        client = Client()
        assert client.baseurl == ""
        assert isinstance(client._config, ClientConfig)
        assert client._auth is None

    def test_init_with_baseurl(self):
        """Test initializing a client with a base URL"""
        baseurl = "https://api.example.com"
        client = Client(baseurl=baseurl)
        assert client.baseurl == baseurl
        assert client._config.baseurl == baseurl

    def test_init_with_auth(self):
        """Test initializing a client with authentication"""
        auth = MagicMock()
        client = Client(auth=auth)
        assert client._auth is auth

    def test_init_with_config(self):
        """Test initializing a client with a config object"""
        config = ClientConfig(
            baseurl="https://api.example.com",
            timeout=60.0,
            verifyssl=False
        )
        client = Client(config=config)
        assert client._config is config
        assert client.baseurl == config.baseurl

    def test_baseurl_overrides_config(self):
        """Test that baseurl param overrides config.baseurl"""
        config = ClientConfig(baseurl="https://old.example.com")
        baseurl = "https://new.example.com"
        client = Client(baseurl=baseurl, config=config)
        assert client.baseurl == baseurl
        assert client._config.baseurl == baseurl

    @patch('clientfactory.client.base.Session')
    def test_create_session(self, mock_session):
        """Test session creation"""
        # Setup
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        auth = MagicMock()
        config = ClientConfig(
            headers={"User-Agent": "Test"},
            cookies={"session": "test"},
            verifyssl=False
        )

        # Execute
        client = Client(auth=auth, config=config)

        # Assert session was created with correct config
        mock_session.assert_called_once()
        call_kwargs = mock_session.call_args.kwargs
        assert call_kwargs["auth"] is auth

        # Check that config was properly translated to session config
        session_config = call_kwargs["config"]
        assert session_config.headers == config.headers
        assert session_config.cookies == config.cookies
        assert session_config.verify == config.verifyssl

    def test_register_resource(self):
        """Test registering a resource class"""
        # Create a mock resource class
        mock_resource_cls = MagicMock()
        mock_resource_cls.__name__ = "MockResource"
        mock_resource_cls._resourceconfig = ResourceConfig(
            name="MockResource",
            path="mockresource"
        )

        # Create a client and register the resource
        client = Client()
        client.register(mock_resource_cls)

        # Check that the resource was registered
        assert "mockresource" in client._resources
        assert hasattr(client, "mockresource")
        assert isinstance(client.mockresource, Resource)

    def test_register_invalid_resource(self):
        """Test registering an invalid resource class"""
        # Create a mock resource class without _resourceconfig
        class InvalidResource:
            pass
        # Create a client
        client = Client()

        # Try to register the invalid resource
        with pytest.raises(ClientError):
            client.register(InvalidResource)

    def test_context_manager(self):
        """Test using client as a context manager"""
        client = Client()
        client.close = MagicMock()

        # Use the client as a context manager
        with client as c:
            assert c is client

        # Check that close was called
        client.close.assert_called_once()
