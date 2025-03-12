# ~/clientfactory/tests/test_utils_request.py
import unittest
from utils.request import (
    Request,
    RequestMethod,
    RequestConfig,
    RequestFactory,
    ValidationError
)

class TestRequest(unittest.TestCase):
    def test_request_initialization(self):
        """Test basic request creation and validation"""
        # Basic GET request
        req = Request(method="GET", url="https://api.example.com/users")
        self.assertEqual(req.method, RequestMethod.GET)
        self.assertEqual(req.url, "https://api.example.com/users")

        # Should handle method as string or enum
        req2 = Request(method=RequestMethod.POST, url="https://api.example.com/users")
        self.assertEqual(req2.method, RequestMethod.POST)

    def test_request_validation(self):
        """Test request validation rules"""
        # Missing URL
        with self.assertRaises(ValidationError):
            Request(method="GET", url="")

        # GET request with body
        with self.assertRaises(ValidationError):
            Request(method="GET", url="http://example.com", json={"key": "value"})

        # Both data and json
        with self.assertRaises(ValidationError):
            Request(
                method="POST",
                url="http://example.com",
                data={"x": 1},
                json={"y": 2}
            )

    def test_request_preparation(self):
        """Test request preparation process"""
        req = Request(
            method="POST",
            url="http://example.com/api",
            json={"key": "value"}
        ).prepare()

        self.assertTrue(req.prepped)
        self.assertEqual(req.headers.get("content-type"), "application/json")

    def test_request_with(self):
        """Test request modification with WITH method"""
        base_req = Request(
            method="GET",
            url="http://example.com",
            headers={"Accept": "application/json"}
        )

        # Test header merging
        new_req = base_req.WITH(headers={"Authorization": "Bearer token"})
        self.assertEqual(new_req.headers["Accept"], "application/json")
        self.assertEqual(new_req.headers["Authorization"], "Bearer token")

        # Test config updating
        new_req = base_req.WITH(config={"timeout": 60.0})
        self.assertEqual(new_req.config.timeout, 60.0)

        # Original request should be unchanged
        self.assertEqual(base_req.config.timeout, 30.0)

        # Test multiple updates
        new_req = base_req.WITH(
            params={"page": 1},
            headers={"X-Custom": "value"},
            config={"maxretries": 5}
        )
        self.assertEqual(new_req.params["page"], 1)
        self.assertEqual(new_req.headers["X-Custom"], "value")
        self.assertEqual(new_req.config.maxretries, 5)

class TestRequestFactory(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory(
            baseurl="https://api.example.com",
            defaultcfg=RequestConfig(timeout=60.0)
        )

    def test_factory_creation(self):
        """Test request creation through factory"""
        req = self.factory.create("GET", "/users")
        self.assertEqual(req.url, "https://api.example.com/users")
        self.assertEqual(req.config.timeout, 60.0)

    def test_factory_convenience_methods(self):
        """Test factory's HTTP method convenience functions"""
        get_req = self.factory.get("/users")
        self.assertEqual(get_req.method, RequestMethod.GET)

        post_req = self.factory.post("/users", json={"name": "test"})
        self.assertEqual(post_req.method, RequestMethod.POST)
        self.assertEqual(post_req.json, {"name": "test"})

        put_req = self.factory.put("/users/1")
        self.assertEqual(put_req.method, RequestMethod.PUT)

        delete_req = self.factory.delete("/users/1")
        self.assertEqual(delete_req.method, RequestMethod.DELETE)

    def test_factory_url_handling(self):
        """Test factory's URL construction behavior"""
        # Should handle paths with or without leading slash
        req1 = self.factory.get("users")
        req2 = self.factory.get("/users")
        self.assertEqual(req1.url, req2.url)

        # Should work without base URL
        local_factory = RequestFactory()
        req = local_factory.get("http://localhost/api")
        self.assertEqual(req.url, "http://localhost/api")

if __name__ == '__main__':
    unittest.main()
