# ~/clientfactory/tests/test_resources.py
import unittest
from unittest.mock import Mock

from session.base import BaseSession
from resources.base import Resource, ResourceConfig, MethodConfig
from resources.decorators import resource, get, post, put, delete
from utils.request import RequestMethod, Request
from utils.response import Response

from loguru import logger as log

class MockSession(BaseSession):
    """Mock session for testing"""
    def __init__(self):
        self.sent_requests = []
        self.mock_response = Response(
            status_code=200,
            headers={},
            raw_content=b'{"success": true}',
            request=Mock()
        )

    def send(self, request: Request) -> Response:
        self.sent_requests.append(request)
        return self.mock_response

class TestResourceBase(unittest.TestCase):
    """Test base Resource class functionality"""

    def setUp(self):
        self.session = MockSession()

        # Create a test resource config
        self.config = ResourceConfig(
            name="users",
            path="users",
            methods={
                "list": MethodConfig(
                    name="list",
                    method=RequestMethod.GET,
                    path=None
                ),
                "get": MethodConfig(
                    name="get",
                    method=RequestMethod.GET,
                    path="{id}"
                )
            }
        )

        self.resource = Resource(self.session, self.config)

    def test_path_construction(self):
        """Test path construction logic"""
        # Base path
        self.assertEqual(
            self.resource.__fullpath__(None),
            "users"
        )

        # With method path
        self.assertEqual(
            self.resource.__fullpath__("test"),
            "users/test"
        )

        # With nested resources
        child_config = ResourceConfig(
            name="posts",
            path="posts",
            parent=self.config
        )
        child = Resource(self.session, child_config)
        self.assertEqual(
            child.__fullpath__("latest"),
            "users/posts/latest"
        )

    def test_request_building(self):
        """Test request construction"""
        cfg = MethodConfig(
            name="test",
            method=RequestMethod.GET,
            path="test/{id}"
        )

        request = self.resource.__build__(cfg, 123, params={"filter": "active"})

        self.assertEqual(request.method, RequestMethod.GET)
        self.assertEqual(request.url, "users/test/123")
        self.assertEqual(request.params, {"filter": "active"})

    def test_method_creation(self):
        """Test method creation and execution"""
        self.assertTrue(hasattr(self.resource, "list"))
        self.assertTrue(hasattr(self.resource, "get"))

        # Test list method
        self.resource.list()
        self.assertEqual(len(self.session.sent_requests), 1)
        self.assertEqual(self.session.sent_requests[0].url, "users")

        # Test get method with parameter
        self.resource.get(123)
        self.assertEqual(len(self.session.sent_requests), 2)
        self.assertEqual(self.session.sent_requests[1].url, "users/123")

class TestResourceDecorators(unittest.TestCase):
    """Test resource decorator functionality"""

    def setUp(self):
        self.session = MockSession()

    def test_basic_resource(self):
        """Test basic resource decoration"""
        @resource
        class Users:
            @get
            def list(self): pass

            @get("{id}")
            def get(self, id): pass

        self.assertTrue(hasattr(Users, '_resourcecfg'))
        self.assertEqual(Users._resourcecfg.name, "Users")
        self.assertEqual(Users._resourcecfg.path, "users")
        self.assertIn("list", Users._resourcecfg.methods)
        self.assertIn("get", Users._resourcecfg.methods)

    def test_nested_resources(self):
        """Test nested resource decoration"""
        @resource
        class Users:
            @get
            def list(self): pass

            @resource
            class Posts:
                @get
                def list(self): pass

                @get("{id}/comments")
                def comments(self, id): pass

        self.assertIn("Posts", Users._resourcecfg.children)
        child_cfg = Users._resourcecfg.children["Posts"]
        self.assertEqual(child_cfg.parent, Users._resourcecfg)
        self.assertIn("comments", child_cfg.methods)

    def test_direct_preprocessing(self):
        """Test preprocessing with direct @preprocess decorator"""
        from resources.decorators import preprocess, resource

        @resource
        class Users:
            @preprocess
            @get
            def list(self, request: Request) -> Request:
                log.debug(f"list method called with request: {request}")
                log.debug(f"list method _methodcfg: {getattr(list, '_methodcfg', None)}")
                log.debug(f"list method _preprocess: {getattr(list, '_preprocess', None)}")
                return request.WITH(headers={"X-Test": "direct"})

        users = Resource(self.session, Users._resourcecfg)
        log.debug(f"Resource config methods: {users._config.methods}")
        log.debug(f"List method config: {users._config.methods.get('list')}")
        users.list()

        sent_request = self.session.sent_requests[0]
        self.assertEqual(sent_request.headers.get("X-Test"), "direct")

    def test_method_preprocessing(self):
        """Test preprocessing with @preprocess(method) reference"""
        from resources.decorators import preprocess, resource
        log.debug(f"starting method preprocessing test")
        @resource
        class Users:
            def add_header(self, request: Request) -> Request:
                return request.WITH(headers={"X-Test": "method"})

            @preprocess(add_header)
            @get
            def list(self): pass

        users = Resource(self.session, Users._resourcecfg)
        users.list()

        sent_request = self.session.sent_requests[0]
        log.debug(f"final request headers: {sent_request.headers}")
        self.assertEqual(sent_request.headers.get("X-Test"), "method")

    def test_direct_postprocessing(self):
        """Test postprocessing with direct @postprocess decorator"""
        from resources.decorators import postprocess, resource

        @resource
        class Users:
            @postprocess
            @get
            def list(self, response: Response) -> Response:
                return response.WITH(headers={"X-Processed": "direct"})

        users = Resource(self.session, Users._resourcecfg)
        response = users.list()

        self.assertEqual(response.headers.get("X-Processed"), "direct")

    def test_method_postprocessing(self):
        """Test postprocessing with @postprocess(method) reference"""
        from resources.decorators import postprocess, resource

        @resource
        class Users:
            def modify_response(self, response: Response) -> Response:
                return response.WITH(headers={"X-Processed": "method"})

            @postprocess(modify_response)
            @get
            def list(self): pass

        users = Resource(self.session, Users._resourcecfg)
        response = users.list()

        self.assertEqual(response.headers.get("X-Processed"), "method")

    def test_combined_processing(self):
        """Test both pre and post processing on same method"""
        from resources.decorators import preprocess, postprocess, resource

        @resource
        class Users:
            def add_request_header(self, request: Request) -> Request:
                return request.WITH(headers={"X-Test": "pre"})

            def add_response_header(self, response: Response) -> Response:
                return response.WITH(headers={"X-Test": "post"})

            @preprocess(add_request_header)
            @postprocess(add_response_header)
            @get
            def list(self): pass

        users = Resource(self.session, Users._resourcecfg)
        response = users.list()

        sent_request = self.session.sent_requests[0]
        self.assertEqual(sent_request.headers.get("X-Test"), "pre")
        self.assertEqual(response.headers.get("X-Test"), "post")

    def test_custom_path(self):
        """Test custom path configuration"""
        @resource(path="api/v1/users")
        class Users:
            @get
            def list(self): pass

        self.assertEqual(Users._resourcecfg.path, "api/v1/users")

if __name__ == '__main__':
    unittest.main()
