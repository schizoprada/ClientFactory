# ~/clientfactory/tests/test_auth_base.py
import unittest
from auth.base import BaseAuth, NoAuth, TokenAuth, BasicAuth, AuthError
from utils.request import Request
from utils.response import Response

class TestBaseAuth(unittest.TestCase):
    def test_no_auth(self):
        """Test NoAuth implementation"""
        auth = NoAuth()
        request = Request(method="GET", url="http://example.com")

        # Should authenticate without doing anything
        state = auth.authenticate()
        self.assertTrue(state.authenticated)

        # Should not modify request
        prepared = auth.prepare(request)
        self.assertEqual(prepared.headers, {})

    def test_token_auth(self):
        """Test TokenAuth implementation"""
        auth = TokenAuth("secret-token")
        request = Request(method="GET", url="http://example.com")

        # Should authenticate with token
        state = auth.authenticate()
        self.assertTrue(state.authenticated)
        self.assertEqual(state.token, "secret-token")

        # Should add token to request
        prepared = auth.prepare(request)
        self.assertEqual(
            prepared.headers["Authorization"],
            "Bearer secret-token"
        )

        # Should raise error if no token
        empty_auth = TokenAuth("")
        self.assertFalse(empty_auth.authenticate().authenticated)
        with self.assertRaises(AuthError):
            empty_auth.prepare(request)

    def test_basic_auth(self):
        """Test BasicAuth implementation"""
        auth = BasicAuth("user", "pass")
        request = Request(method="GET", url="http://example.com")

        # Should authenticate with credentials
        state = auth.authenticate()
        self.assertTrue(state.authenticated)

        # Should add basic auth header
        prepared = auth.prepare(request)
        self.assertTrue(
            prepared.headers["Authorization"].startswith("Basic ")
        )

        # Should raise error if missing credentials
        empty_auth = BasicAuth("", "")
        self.assertFalse(empty_auth.authenticate().authenticated)
        with self.assertRaises(AuthError):
            empty_auth.prepare(request)

    def test_auth_response_handling(self):
        """Test response handling"""
        auth = NoAuth()  # Use NoAuth for testing base behavior

        # Test 401 response
        unauth_response = Response(
            status_code=401,
            headers={},
            raw_content=b'',
            request=Request(method="GET", url="http://example.com")
        )
        with self.assertRaises(AuthError):
            auth.handle(unauth_response)
        self.assertFalse(auth.state.authenticated)

        # Test 403 response
        forbidden_response = Response(
            status_code=403,
            headers={},
            raw_content=b'',
            request=Request(method="GET", url="http://example.com")
        )
        with self.assertRaises(AuthError):
            auth.handle(forbidden_response)

if __name__ == '__main__':
    unittest.main()
