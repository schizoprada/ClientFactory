# ~/clientfactory/tests/test_auth_oauth.py
# ~/clientfactory/tests/test_auth_oauth.py
import unittest
from unittest.mock import Mock, patch
from time import time
import requests

from auth.oauth import OAuth2Auth, OAuth2Config, OAuth2Token, AuthError
from utils.request import Request, RequestMethod

class TestOAuth2Auth(unittest.TestCase):
    """Test OAuth2 authentication functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.config = OAuth2Config(
            clientid="testclient",
            clientsecret="testsecret",
            tokenurl="https://api.test/token",
            authurl="https://api.test/auth",
            redirecturi="http://localhost/callback",
            scope="read write"
        )
        self.auth = OAuth2Auth(self.config)

        # Mock successful token response
        self.token_response = {
            "accesstoken": "testtoken",
            "tokentype": "Bearer",
            "expiresin": 3600,
            "refreshtoken": "refreshtoken",
            "scope": "read write"
        }

    def test_client_credentials_init(self):
        """Test client credentials flow initialization"""
        auth = OAuth2Auth.clientcredentials(
            clientid="testclient",
            clientsecret="testsecret",
            tokenurl="https://api.test/token",
            scope="read write"
        )

        self.assertEqual(auth.config.clientid, "testclient")
        self.assertEqual(auth.config.clientsecret, "testsecret")
        self.assertEqual(auth.config.tokenurl, "https://api.test/token")
        self.assertEqual(auth.config.scope, "read write")

    def test_authorization_code_init(self):
        """Test authorization code flow initialization"""
        auth = OAuth2Auth.authorizationcode(
            clientid="testclient",
            clientsecret="testsecret",
            authurl="https://api.test/auth",
            tokenurl="https://api.test/token",
            redirecturi="http://localhost/callback"
        )

        self.assertEqual(auth.config.clientid, "testclient")
        self.assertEqual(auth.config.authurl, "https://api.test/auth")
        self.assertEqual(auth.config.redirecturi, "http://localhost/callback")

    def test_get_auth_url(self):
        """Test authorization URL generation"""
        url = self.auth.getauthurl(state="teststate")

        self.assertIn("clientid=testclient", url)
        self.assertIn("response_type=code", url)
        self.assertIn("redirecturi=http", url)
        self.assertIn("state=teststate", url)
        self.assertIn("scope=read+write", url)

    @patch('requests.post')
    def test_authenticate_success(self, mock_post):
        """Test successful client credentials authentication"""
        mock_response = Mock()
        mock_response.json.return_value = self.token_response
        mock_post.return_value = mock_response

        state = self.auth.authenticate()

        self.assertTrue(state.authenticated)
        self.assertEqual(state.token, "testtoken")
        self.assertIsNotNone(state.expires)

        # Verify correct request
        call_args = mock_post.call_args[1]
        self.assertEqual(call_args['data']['grant_type'], "clientcredentials")
        self.assertEqual(call_args['data']['clientid'], "testclient")

    @patch('requests.post')
    def test_authenticate_failure(self, mock_post):
        """Test failed authentication"""
        mock_post.side_effect = requests.RequestException("Test error")

        with self.assertRaises(AuthError):
            self.auth.authenticate()

    @patch('requests.post')
    def test_auth_with_code(self, mock_post):
        """Test authorization code exchange"""
        mock_response = Mock()
        mock_response.json.return_value = self.token_response
        mock_post.return_value = mock_response

        state = self.auth.authwithcode("testcode")

        self.assertTrue(state.authenticated)
        self.assertEqual(state.token, "testtoken")

        # Verify correct request
        call_args = mock_post.call_args[1]
        self.assertEqual(call_args['data']['grant_type'], "authorizationcode")
        self.assertEqual(call_args['data']['code'], "testcode")

    @patch('requests.post')
    def test_refresh_token(self, mock_post):
        """Test token refresh"""
        # First authenticate to get initial token
        mock_response = Mock()
        mock_response.json.return_value = self.token_response
        mock_post.return_value = mock_response

        self.auth.authenticate()

        # Now test refresh
        new_token = {**self.token_response, "accesstoken": "newtoken"}
        mock_response.json.return_value = new_token

        success = self.auth.refresh()

        self.assertTrue(success)
        self.assertEqual(self.auth.state.token, "newtoken")

    def test_token_expiration(self):
        """Test token expiration checking"""
        token = OAuth2Token(
            accesstoken="test",
            tokentype="Bearer",
            expiresin=3600,
            createdat=time() - 4000  # Created more than expiresin ago
        )

        self.assertTrue(token.expired)

        token = OAuth2Token(
            accesstoken="test",
            tokentype="Bearer",
            expiresin=3600,
            createdat=time()  # Just created
        )

        self.assertFalse(token.expired)

    def test_request_preparation(self):
        """Test token addition to requests"""
        # Setup token
        self.auth._token = OAuth2Token(
            accesstoken="testtoken",
            tokentype="Bearer",
            expiresin=3600,
            createdat=time()
        )
        self.auth.state.authenticated = True

        # Test header placement
        request = Request(method=RequestMethod.GET, url="https://api.test/resource")
        prepped = self.auth.prepare(request)
        self.assertEqual(
            prepped.headers["Authorization"],
            "Bearer testtoken"
        )

        # Test query placement
        self.auth.config.tokenplacement = "query"
        prepped = self.auth.prepare(request)
        self.assertEqual(
            prepped.params["accesstoken"],
            "testtoken"
        )

        # Test body placement with GET (should fallback to query params)
        self.auth.config.tokenplacement = "body"
        prepped = self.auth.prepare(request)
        self.assertEqual(
            prepped.params["accesstoken"],
            "testtoken"
        )

        # Test body placement with POST
        request = Request(method=RequestMethod.POST, url="https://api.test/resource")
        prepped = self.auth.prepare(request)
        self.assertEqual(
            prepped.data["accesstoken"],
            "testtoken"
        )

    def test_error_handling(self):
        """Test various error conditions"""
        # Test prepare without authentication
        request = Request(method=RequestMethod.GET, url="https://api.test/resource")
        with self.assertRaises(AuthError):
            self.auth.prepare(request)

        # Test invalid token placement
        self.auth._token = OAuth2Token(
            accesstoken="test",
            tokentype="Bearer"
        )
        self.auth.config.tokenplacement = "invalid"
        with self.assertRaises(AuthError):
            self.auth.prepare(request)

        # Test auth URL without configuration
        auth = OAuth2Auth(OAuth2Config(
            clientid="test",
            clientsecret="test",
            tokenurl="https://api.test/token"
        ))
        with self.assertRaises(AuthError):
            auth.getauthurl()

if __name__ == '__main__':
    unittest.main()
