# ~/clientfactory/tests/test_client.py
import unittest
from client import Client, ClientConfig
from auth.apikey import ApiKeyAuth
from resources.decorators import resource, get
from utils.request import RequestConfig

class TestClient(unittest.TestCase):
    """Test client functionality"""

    def test_class_based_client(self):
        """Test class-based client pattern"""

        class TestAPI(Client):
            baseurl = "https://api.test.com"
            auth = ApiKeyAuth("test-key")

            @resource
            class Items:
                @get("items")
                def list_items(self): pass

                @get("items/{id}")
                def get_item(self, id): pass

        client = TestAPI()

        # Check configuration
        self.assertEqual(client.baseurl, "https://api.test.com")
        self.assertIsInstance(client.auth, ApiKeyAuth)

        # Check resource setup
        self.assertIn("items", client._resources)
        self.assertTrue(hasattr(client, "items"))
        self.assertTrue(callable(client.items.list_items))
        self.assertTrue(callable(client.items.get_item))

    def test_constructor_override(self):
        """Test constructor argument overrides"""

        class TestAPI(Client):
            baseurl = "https://api.test.com"
            auth = ApiKeyAuth("test-key")

        # Override with constructor args
        client = TestAPI(
            baseurl="https://override.com",
            auth=ApiKeyAuth("new-key")
        )

        self.assertEqual(client.baseurl, "https://override.com")
        self.assertEqual(client.auth.config.key, "new-key")

    def test_manual_resource_registration(self):
        """Test manual resource registration"""

        @resource
        class Items:
            @get("items")
            def list_items(self): pass

        client = Client(baseurl="https://api.test.com")
        client.register(Items)

        self.assertIn("items", client._resources)
        self.assertTrue(hasattr(client, "items"))
        self.assertTrue(callable(client.items.list_items))

    def test_invalid_resource_registration(self):
        """Test registration of invalid resource"""

        class NotAResource:
            pass

        client = Client()
        with self.assertRaises(ValueError):
            client.register(NotAResource)

    def test_context_manager(self):
        """Test client as context manager"""

        with Client() as client:
            self.assertIsInstance(client, Client)
        # Session should be closed after context

if __name__ == '__main__':
    unittest.main()
