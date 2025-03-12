# ~/clientfactory/tests/test_resources_base_matmul.py
import unittest
from unittest.mock import Mock
from resources.base import Resource, ResourceConfig
from resources.decorators import get, post, MethodConfig
from utils.request import RequestMethod
from loguru import logger as log

class TestResourceMethodRegistration(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.config = ResourceConfig(
            name="test",
            path="test",
            methods={},
            children={}
        )
        self.resource = Resource(session=self.session, config=self.config)

    def test_basic_method_registration(self):
        """Test basic method registration with default GET method"""
        def my_method(self):
            return "test method"

        self.resource @ my_method
        self.assertTrue(hasattr(self.resource, 'my_method'))
        self.assertEqual(self.resource.my_method(), "test method")

    def test_custom_named_method(self):
        """Test method registration with custom name"""
        def my_method(self):
            return "test method"

        self.resource @ "custom" @ my_method
        self.assertTrue(hasattr(self.resource, 'custom'))
        self.assertFalse(hasattr(self.resource, 'my_method'))
        self.assertEqual(self.resource.custom(), "test method")

    def test_method_with_http_method(self):
        """Test method registration with specific HTTP method"""
        def create_item(self):
            return "create method"

        self.resource @ (create_item, 'POST')
        self.assertTrue(hasattr(self.resource, 'create_item'))
        bound_method = getattr(self.resource, 'create_item')
        self.assertTrue(hasattr(bound_method, '_methodcfg'))
        self.assertEqual(bound_method._methodcfg.method, RequestMethod.POST)

    def test_decorated_method(self):
        """Test registration of already decorated method"""
        @post("items")
        def create_item(self):
            return "create method"

        self.resource @ create_item
        self.assertTrue(hasattr(self.resource, 'create_item'))
        bound_method = getattr(self.resource, 'create_item')
        self.assertTrue(hasattr(bound_method, '_methodcfg'))
        self.assertEqual(bound_method._methodcfg.method, RequestMethod.POST)

    def test_method_chaining(self):
        """Test chaining multiple method registrations"""
        def method1(self): return "method1"
        def method2(self): return "method2"

        self.resource @ method1 @ method2
        self.assertTrue(hasattr(self.resource, 'method1'))
        self.assertTrue(hasattr(self.resource, 'method2'))
        self.assertEqual(self.resource.method1(), "method1")
        self.assertEqual(self.resource.method2(), "method2")

    def test_mixed_registration(self):
        """Test mixing different registration styles"""
        def method1(self): return "method1"

        # Chain registrations one at a time for clarity
        self.resource @ "custom" @ (method1, 'PUT')

        @get("items")
        def get_items(self): return "get items"

        self.resource @ get_items

        # Verify methods
        self.assertTrue(hasattr(self.resource, 'custom'))
        self.assertTrue(hasattr(self.resource, 'items'))

        custom_method = getattr(self.resource, 'custom')
        self.assertTrue(hasattr(custom_method, '_methodcfg'))
        self.assertEqual(custom_method._methodcfg.method, RequestMethod.PUT)

        items_method = getattr(self.resource, 'get_items')
        self.assertTrue(hasattr(items_method, '_methodcfg'))
        self.assertEqual(items_method._methodcfg.method, RequestMethod.GET)

    def test_method_with_processors(self):
        """Test method registration with pre/post processors"""
        def preprocess(request):
            return request

        def postprocess(response):
            return response

        def my_method(self):
            return "test method"

        # Set processors
        my_method._preprocess = preprocess
        my_method._postprocess = postprocess

        self.resource @ my_method
        bound_method = getattr(self.resource, 'my_method')
        self.assertTrue(hasattr(bound_method, '_methodcfg'))
        self.assertEqual(bound_method._methodcfg.preprocess, preprocess)
        self.assertEqual(bound_method._methodcfg.postprocess, postprocess)

    def test_invalid_method_spec(self):
        """Test invalid method specification"""
        def my_method(self):
            return "test method"

        with self.assertRaises(ValueError):
            self.resource @ (my_method, "INVALID")

    def test_rename_decorated_method(self):
        """Test renaming an already decorated method"""
        @get("items")
        def list_items(self):
            return "list items"

        self.resource @ "get_all" @ list_items
        self.assertTrue(hasattr(self.resource, 'get_all'))
        self.assertFalse(hasattr(self.resource, 'list_items'))
        bound_method = getattr(self.resource, 'get_all')
        self.assertTrue(hasattr(bound_method, '_methodcfg'))
        self.assertEqual(bound_method._methodcfg.method, RequestMethod.GET)

if __name__ == '__main__':
    unittest.main()
