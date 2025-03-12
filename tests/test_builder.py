# ~/clientfactory/tests/test_builder.py
import unittest
from builder import ClientBuilder
from auth.apikey import ApiKeyAuth
from resources.decorators import resource, get
from client import Client

class TestClientBuilder(unittest.TestCase):
    """Test ClientBuilder functionality"""

    def test_basic_build(self):
        """Test basic builder usage"""
        client = ClientBuilder()\
            .baseurl("https://api.test.com")\
            .build()

        self.assertIsInstance(client, Client)
        self.assertEqual(client.baseurl, "https://api.test.com")

    def test_auth_configuration(self):
        """Test auth configuration"""
        auth = ApiKeyAuth("test-key")

        client = ClientBuilder()\
            .baseurl("https://api.test.com")\
            .auth(auth)\
            .build()

        self.assertEqual(client.auth, auth)

    def test_resource_registration(self):
        """Test resource registration"""
        @resource
        class TestResource:
            @get("test")
            def test_method(self): pass

        client = ClientBuilder()\
            .baseurl("https://api.test.com")\
            .addresource(TestResource)\
            .build()

        self.assertTrue(hasattr(client, "testresource"))
        self.assertTrue(callable(client.testresource.test_method))

    def test_session_configuration(self):
        """Test session configuration"""
        headers = {"User-Agent": "TestClient/1.0"}
        cookies = {"session": "abc123"}

        client = ClientBuilder()\
            .headers(headers)\
            .cookies(cookies)\
            .verifyssl(False)\
            .build()

        self.assertEqual(
            client._session.config.headers,
            headers
        )
        self.assertEqual(
            client._session.config.cookies,
            cookies
        )
        self.assertEqual(
            client._session.config.verify,
            False
        )

    def test_request_configuration(self):
        """Test request configuration"""
        client = ClientBuilder()\
            .timeout(60.0)\
            .requestconfig(
                maxretries=5,
                retrybackoff=2.0
            )\
            .build()

        self.assertEqual(
            client.config.request.timeout,
            60.0
        )
        self.assertEqual(
            client.config.request.maxretries,
            5
        )
        self.assertEqual(
            client.config.request.retrybackoff,
            2.0
        )

    def test_chaining(self):
        """Test method chaining"""
        auth = ApiKeyAuth("test-key")
        headers = {"User-Agent": "TestClient/1.0"}

        @resource
        class TestResource:
            @get("test")
            def test_method(self): pass

        client = ClientBuilder()\
            .baseurl("https://api.test.com")\
            .auth(auth)\
            .headers(headers)\
            .timeout(30.0)\
            .addresource(TestResource)\
            .build()

        # Verify everything was configured
        self.assertEqual(client.baseurl, "https://api.test.com")
        self.assertEqual(client.auth, auth)
        self.assertEqual(
            client._session.config.headers,
            headers
        )
        self.assertEqual(
            client.config.request.timeout,
            30.0
        )
        self.assertTrue(hasattr(client, "testresource"))

if __name__ == '__main__':
    unittest.main()
