# ~/clientfactory/tests/test_auth_apikey.py
import unittest
from auth.apikey import ApiKeyAuth, ApiKeyLocation, AuthError
from utils.request import Request, RequestMethod

class TestApiKeyAuth(unittest.TestCase):
    """Test ApiKeyAuth functionality"""

    def setUp(self):
        self.request = Request(
            method=RequestMethod.GET,
            url="https://api.example.com/test"
        )

    def test_header_auth(self):
        """Test header-based authentication"""
        auth = ApiKeyAuth("test-key")
        prepped = auth.prepare(self.request)

        self.assertEqual(
            prepped.headers.get("X-Api-Key"),
            "test-key"
        )

    def test_query_auth(self):
        """Test query parameter authentication"""
        auth = ApiKeyAuth("test-key", location="query", name="api_key")
        prepped = auth.prepare(self.request)

        self.assertEqual(
            prepped.params.get("api_key"),
            "test-key"
        )

    def test_custom_header(self):
        """Test custom header name and prefix"""
        auth = ApiKeyAuth(
            "test-key",
            name="Authorization",
            prefix="Bearer"
        )
        prepped = auth.prepare(self.request)

        self.assertEqual(
            prepped.headers.get("Authorization"),
            "Bearer test-key"
        )

    def test_convenience_methods(self):
        """Test class convenience methods"""
        # Header auth
        auth1 = ApiKeyAuth.header("test-key", name="Custom-Key")
        prepped1 = auth1.prepare(self.request)
        self.assertEqual(
            prepped1.headers.get("Custom-Key"),
            "test-key"
        )

        # Query auth
        auth2 = ApiKeyAuth.query("test-key", name="token")
        prepped2 = auth2.prepare(self.request)
        self.assertEqual(
            prepped2.params.get("token"),
            "test-key"
        )

    def test_invalid_location(self):
        """Test invalid location handling"""
        with self.assertRaises(AuthError):
            ApiKeyAuth("test-key", location="invalid")

    def test_empty_key(self):
        """Test empty key handling"""
        auth = ApiKeyAuth("")
        with self.assertRaises(AuthError):
            auth.authenticate()

    def test_authentication_state(self):
        """Test authentication state management"""
        auth = ApiKeyAuth("test-key")

        # Should start unauthenticated
        self.assertFalse(auth.isauthenticated)

        # Should authenticate on prepare
        auth.prepare(self.request)
        self.assertTrue(auth.isauthenticated)
        self.assertEqual(auth.state.token, "test-key")

if __name__ == '__main__':
    unittest.main()
