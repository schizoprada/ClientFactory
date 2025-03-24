# ~/ClientFactory/tests/unit/client/test_builder.py
import pytest
from unittest.mock import MagicMock, patch

from clientfactory.client import ClientBuilder, Client, ClientConfig


class TestClientBuilder:
    """Tests for the ClientBuilder class"""

    def test_init(self):
        """Test initializing a builder"""
        builder = ClientBuilder()
        assert isinstance(builder._config, ClientConfig)
        assert builder._auth is None
        assert builder._resources == []

    def test_baseurl(self):
        """Test setting the base URL"""
        builder = ClientBuilder()
        url = "https://api.example.com"
        result = builder.baseurl(url)
        assert result is builder  # Test method chaining returns self
        assert builder._config.baseurl == url

    def test_auth(self):
        """Test setting the authentication handler"""
        builder = ClientBuilder()
        auth = MagicMock()
        result = builder.auth(auth)
        assert result is builder
        assert builder._auth is auth

    def test_headers(self):
        """Test setting headers"""
        builder = ClientBuilder()
        headers = {"User-Agent": "Test", "X-Api-Key": "123"}
        result = builder.headers(headers)
        assert result is builder
        assert builder._config.headers == headers

    def test_headers_update(self):
        """Test that headers are updated, not replaced"""
        builder = ClientBuilder()
        # Set initial headers
        builder.headers({"User-Agent": "Test"})
        # Update with additional headers
        builder.headers({"X-Api-Key": "123"})
        assert builder._config.headers == {
            "User-Agent": "Test",
            "X-Api-Key": "123"
        }

    def test_cookies(self):
        """Test setting cookies"""
        builder = ClientBuilder()
        cookies = {"session": "abc123"}
        result = builder.cookies(cookies)
        assert result is builder
        assert builder._config.cookies == cookies

    def test_verifyssl(self):
        """Test configuring SSL verification"""
        builder = ClientBuilder()
        # Default should be True
        assert builder._config.verifyssl is True
        # Set to False
        result = builder.verifyssl(False)
        assert result is builder
        assert builder._config.verifyssl is False

    def test_timeout(self):
        """Test setting request timeout"""
        builder = ClientBuilder()
        timeout = 60.0
        result = builder.timeout(timeout)
        assert result is builder
        assert builder._config.timeout == timeout

    def test_followredirects(self):
        """Test configuring redirect following"""
        builder = ClientBuilder()
        # Default should be True
        assert builder._config.followredirects is True
        # Set to False
        result = builder.followredirects(False)
        assert result is builder
        assert builder._config.followredirects is False

    def test_register_resource(self):
        """Test registering a resource class"""
        builder = ClientBuilder()
        resource = MagicMock()
        result = builder.register(resource)
        assert result is builder
        assert builder._resources == [resource]

    @patch('clientfactory.client.builder.Client')
    def test_build(self, mock_client):
        """Test building a client"""
        # Setup
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        builder = ClientBuilder()
        builder.baseurl("https://api.example.com")
        builder.timeout(60.0)
        builder.verifyssl(False)

        auth = MagicMock()
        builder.auth(auth)

        resource1 = MagicMock()
        resource2 = MagicMock()
        builder.register(resource1)
        builder.register(resource2)

        # Execute
        client = builder.build()

        # Verify
        assert client is mock_client_instance

        # Verify client was created with correct params
        mock_client.assert_called_once_with(
            baseurl=builder._config.baseurl,
            auth=auth,
            config=builder._config
        )

        # Verify resources were registered
        assert mock_client_instance.register.call_count == 2
        mock_client_instance.register.assert_any_call(resource1)
        mock_client_instance.register.assert_any_call(resource2)

    def test_method_chaining(self):
        """Test full method chaining"""
        with patch('clientfactory.client.builder.Client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance

            auth = MagicMock()
            resource = MagicMock()

            # Chain all methods
            client = (
                ClientBuilder()
                .baseurl("https://api.example.com")
                .auth(auth)
                .headers({"User-Agent": "Test"})
                .cookies({"session": "abc123"})
                .verifyssl(True)
                .timeout(60.0)
                .followredirects(True)
                .register(resource)
                .build()
            )

            assert client is mock_client_instance
            mock_client_instance.register.assert_called_once_with(resource)
