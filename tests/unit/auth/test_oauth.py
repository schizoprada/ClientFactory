# ~/ClientFactory/tests/unit/auth/test_oauth.py
"""
Unit tests for the OAuthAuth class
"""
import pytest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from clientfactory.auth.oauth import OAuthAuth, OAuthConfig, OAuthToken, OAuthFlow, OAuthError
from clientfactory.auth.tokens import TokenScheme
from clientfactory.core import Request, RequestMethod


@pytest.fixture
def mock_token_response():
    """Create a mock token response"""
    return {
        "access_token": "test-access-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "test-refresh-token",
        "scope": "read write"
    }


@pytest.fixture
def oauth_config():
    """Create a standard OAuth config for testing"""
    return OAuthConfig(
        clientid="test-client",
        clientsecret="test-secret",
        tokenurl="https://auth.example.com/token",
        authurl="https://auth.example.com/authorize",
        redirecturi="https://client.example.com/callback",
        scope="read write"
    )


def test_init(oauth_config):
    """Test initialization"""
    # Basic initialization
    auth = OAuthAuth(oauth_config)
    assert auth.config == oauth_config
    assert auth._token is None
    assert not auth.state.authenticated

    # Initialization with token
    token = OAuthToken(
        accesstoken="test-token",
        tokentype=TokenScheme.BEARER,
        expiresin=3600,
        refreshtoken="test-refresh",
        scope="read write"
    )
    auth = OAuthAuth(oauth_config, token)
    assert auth._token == token
    assert auth.state.authenticated
    assert auth.state.token == "test-token"


def test_authenticate_client_credentials(oauth_config, mock_token_response):
    """Test authentication with client credentials flow"""
    with patch('clientfactory.auth.oauth.rq.post') as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        # Test authentication
        auth = OAuthAuth(oauth_config)
        assert auth.authenticate()

        # Check that post was called with correct parameters
        mock_post.assert_called_once_with(
            oauth_config.tokenurl,
            data={
                "grant_type": "client_credentials",
                "client_id": oauth_config.clientid,
                "client_secret": oauth_config.clientsecret,
                "scope": oauth_config.scope
            },
            headers={}
        )

        # Check token was set correctly
        assert auth._token is not None
        assert auth._token.accesstoken == "test-access-token"
        assert auth._token.tokentype == TokenScheme.BEARER
        assert auth._token.expiresin == 3600
        assert auth._token.refreshtoken == "test-refresh-token"
        assert auth._token.scope == "read write"

        # Check auth state was updated
        assert auth.state.authenticated
        assert auth.state.token == "test-access-token"
        assert auth.state.expires is not None


def test_authenticate_failure(oauth_config):
    """Test authentication failure"""
    with patch('clientfactory.auth.oauth.rq.post') as mock_post:
        # Setup mock response to fail
        mock_post.side_effect = Exception("Token request failed")

        # Test authentication
        auth = OAuthAuth(oauth_config)
        with pytest.raises(OAuthError):
            auth.authenticate()

        # Check that state was not updated
        assert not auth.state.authenticated
        assert auth._token is None


def test_prepare(oauth_config):
    """Test request preparation"""
    # Create token
    token = OAuthToken(
        accesstoken="test-token",
        tokentype=TokenScheme.BEARER,
        expiresin=3600
    )

    # Create auth with token
    auth = OAuthAuth(oauth_config, token)

    # Create a request
    request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

    # Prepare the request
    prepared = auth.prepare(request)

    # Check that Authorization header was added
    assert "Authorization" in prepared.headers
    assert prepared.headers["Authorization"] == "Bearer test-token"


def test_prepare_without_token(oauth_config, mock_token_response):
    """Test preparing a request without a token triggers authentication"""
    with patch('clientfactory.auth.oauth.rq.post') as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        # Create auth without token
        auth = OAuthAuth(oauth_config)

        # Create a request
        request = Request(method=RequestMethod.GET, url="https://api.example.com/test")

        # Prepare the request (should trigger authentication)
        prepared = auth.prepare(request)

        # Check that post was called
        mock_post.assert_called_once()

        # Check that Authorization header was added
        assert "Authorization" in prepared.headers
        assert prepared.headers["Authorization"] == "Bearer test-access-token"


def test_refresh_token(oauth_config, mock_token_response):
    """Test refreshing a token"""
    # Create token with refresh token
    token = OAuthToken(
        accesstoken="old-token",
        tokentype=TokenScheme.BEARER,
        expiresin=3600,
        refreshtoken="test-refresh"
    )

    with patch('clientfactory.auth.oauth.rq.post') as mock_post:
        # Setup mock response with new token
        mock_response = MagicMock()
        new_token_data = mock_token_response.copy()
        new_token_data["access_token"] = "new-token"
        mock_response.json.return_value = new_token_data
        mock_post.return_value = mock_response

        # Create auth with token
        auth = OAuthAuth(oauth_config, token)

        # Refresh token
        assert auth.refresh()

        # Check that post was called with correct parameters
        mock_post.assert_called_once_with(
            oauth_config.tokenurl,
            data={
                "grant_type": "refresh_token",
                "refresh_token": "test-refresh",
                "client_id": oauth_config.clientid,
                "client_secret": oauth_config.clientsecret
            },
            headers={}
        )

        # Check token was updated
        assert auth._token.accesstoken == "new-token"
        assert auth.state.token == "new-token"


def test_refresh_token_failure(oauth_config):
    """Test refresh token failure"""
    # Create token with refresh token
    token = OAuthToken(
        accesstoken="old-token",
        tokentype=TokenScheme.BEARER,
        expiresin=3600,
        refreshtoken="test-refresh"
    )

    with patch('clientfactory.auth.oauth.rq.post') as mock_post:
        # Setup mock response to fail
        mock_post.side_effect = Exception("Token refresh failed")

        # Create auth with token
        auth = OAuthAuth(oauth_config, token)

        # Refresh token should raise error
        with pytest.raises(OAuthError):
            auth.refresh()

        # Check auth state was updated
        assert not auth.state.authenticated


def test_refresh_without_refresh_token(oauth_config, mock_token_response):
    """Test refresh without refresh token falls back to full authentication"""
    # Create token without refresh token
    token = OAuthToken(
        accesstoken="old-token",
        tokentype=TokenScheme.BEARER,
        expiresin=3600
    )

    with patch('clientfactory.auth.oauth.rq.post') as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        # Create auth with token
        auth = OAuthAuth(oauth_config, token)

        # Refresh token (should fall back to authenticate)
        assert auth.refresh()

        # Check that post was called with client credentials
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]['data']
        assert call_args["grant_type"] == "client_credentials"


def test_authorize_url(oauth_config):
    """Test generating authorization URL"""
    import urllib.parse

    auth = OAuthAuth(oauth_config)
    url = auth.authorizeurl(state="test-state")

    # Parse the URL to get the query parameters
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Check that base URL is correct
    assert parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path == oauth_config.authurl

    # Check that the expected query parameters are present with correct values
    assert query_params.get('client_id') == [oauth_config.clientid]
    assert query_params.get('redirect_uri') == [oauth_config.redirecturi]
    assert query_params.get('scope') == [oauth_config.scope]
    assert query_params.get('response_type') == ['code']
    assert query_params.get('state') == ['test-state']


def test_authorize_url_missing_config():
    """Test generating authorization URL with missing configuration"""
    # No auth URL
    config = OAuthConfig(
        clientid="test-client",
        clientsecret="test-secret",
        tokenurl="https://auth.example.com/token",
        redirecturi="https://client.example.com/callback"
    )
    auth = OAuthAuth(config)
    with pytest.raises(OAuthError):
        auth.authorizeurl()

    # No redirect URI
    config = OAuthConfig(
        clientid="test-client",
        clientsecret="test-secret",
        tokenurl="https://auth.example.com/token",
        authurl="https://auth.example.com/authorize"
    )
    auth = OAuthAuth(config)
    with pytest.raises(OAuthError):
        auth.authorizeurl()


def test_exchange_code(oauth_config, mock_token_response):
    """Test exchanging authorization code for tokens"""
    with patch('clientfactory.auth.oauth.rq.post') as mock_post:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        # Create auth
        auth = OAuthAuth(oauth_config)

        # Exchange code
        assert auth.exchangecode("test-code")

        # Check that post was called with correct parameters
        mock_post.assert_called_once_with(
            oauth_config.tokenurl,
            data={
                "grant_type": "authorization_code",
                "code": "test-code",
                "client_id": oauth_config.clientid,
                "client_secret": oauth_config.clientsecret,
                "redirect_uri": oauth_config.redirecturi
            },
            headers={}
        )

        # Check token was set correctly
        assert auth._token is not None
        assert auth._token.accesstoken == "test-access-token"

        # Check auth state was updated
        assert auth.state.authenticated
        assert auth.state.token == "test-access-token"


def test_class_methods():
    """Test the class methods for creating OAuth instances"""
    # Test ClientCredentials
    auth = OAuthAuth.ClientCredentials(
        clientid="test-client",
        clientsecret="test-secret",
        tokenurl="https://auth.example.com/token",
        scope="read write"
    )
    assert auth.config.clientid == "test-client"
    assert auth.config.clientsecret == "test-secret"
    assert auth.config.tokenurl == "https://auth.example.com/token"
    assert auth.config.scope == "read write"
    assert auth.config.flow == OAuthFlow.CLIENTCREDENTIALS

    # Test AuthorizationCode
    auth = OAuthAuth.AuthorizationCode(
        clientid="test-client",
        clientsecret="test-secret",
        authurl="https://auth.example.com/authorize",
        tokenurl="https://auth.example.com/token",
        redirecturi="https://client.example.com/callback"
    )
    assert auth.config.authurl == "https://auth.example.com/authorize"
    assert auth.config.redirecturi == "https://client.example.com/callback"
    assert auth.config.flow == OAuthFlow.AUTHORIZATIONCODE
