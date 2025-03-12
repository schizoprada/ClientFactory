# ~/clientfactory/tests/test_client_matmul.py
import unittest
from client import Client
from resources.decorators import resource, get
from utils.request import RequestMethod
from loguru import logger as log

class TestClientRegistration(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    def test_method_registration(self):
        def my_method(self):
            return "test method"

        log.debug("Registering basic method")
        self.client @ my_method
        log.debug(f"Client attributes after registration: {dir(self.client)}")
        self.assertTrue(hasattr(self.client, 'my_method'))
        self.assertEqual(self.client.my_method(), "test method")

    def test_method_with_http_method(self):
        def post_data(self):
            return "post method"

        log.debug("Registering method with HTTP method")
        self.client @ (post_data, 'POST')
        log.debug(f"Client attributes after registration: {dir(self.client)}")
        self.assertTrue(hasattr(self.client, 'post_data'))
        bound_method = getattr(self.client, 'post_data')
        self.assertTrue(hasattr(bound_method, '_methodcfg'))
        self.assertEqual(bound_method._methodcfg.method, RequestMethod.POST)

    def test_resource_registration(self):
        @resource
        class Users:
            @get("users")
            def list(self): pass

        log.debug("Registering decorated resource")
        self.client @ Users
        log.debug(f"Client attributes after registration: {dir(self.client)}")
        log.debug(f"Client resources: {getattr(self.client, '_resources', {})}")
        self.assertTrue(hasattr(self.client, 'users'))
        self.assertTrue(hasattr(self.client.users, 'list'))

    def test_custom_named_resource(self):
        @resource
        class Products:
            @get("products")
            def list(self): pass

        log.debug("Registering resource with custom name")
        self.client @ "items" @ Products
        log.debug(f"Client attributes after registration: {dir(self.client)}")
        self.assertTrue(hasattr(self.client, 'items'))
        self.assertFalse(hasattr(self.client, 'products'))
        self.assertTrue(hasattr(self.client.items, 'list'))

    def test_undecorated_resource(self):
        class Categories:
            @get("categories")
            def list(self): pass

        log.debug("Registering undecorated resource")
        self.client @ Categories
        log.debug(f"Client attributes after registration: {dir(self.client)}")
        self.assertTrue(hasattr(self.client, 'categories'))
        self.assertTrue(hasattr(self.client.categories, 'list'))

if __name__ == '__main__':
    unittest.main()
