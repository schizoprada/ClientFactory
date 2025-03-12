# ~/clientfactory/tests/test_utils_response.py
import unittest
from utils.response import Response, HTTPError, ResponseError
from utils.request import Request

class TestResponse(unittest.TestCase):
    def setUp(self):
        self.request = Request(method="GET", url="http://example.com")

    def test_response_basics(self):
        """Test basic response properties"""
        resp = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            raw_content=b'{"key": "value"}',
            request=self.request
        )

        self.assertTrue(resp.ok)
        self.assertEqual(resp.reason, "OK")
        self.assertEqual(resp.text, '{"key": "value"}')

    def test_json_parsing(self):
        """Test JSON parsing and caching"""
        resp = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            raw_content=b'{"key": "value"}',
            request=self.request
        )

        # Test parsing
        data = resp.json()
        self.assertEqual(data["key"], "value")

        # Test caching
        self.assertIs(data, resp.json())

        # Test invalid JSON
        bad_resp = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            raw_content=b'invalid json',
            request=self.request
        )
        with self.assertRaises(ResponseError):
            bad_resp.json()

    def test_error_handling(self):
        """Test error status handling"""
        resp = Response(
            status_code=404,
            headers={},
            raw_content=b'Not Found',
            request=self.request
        )

        self.assertFalse(resp.ok)
        with self.assertRaises(HTTPError) as cm:
            resp.raise_for_status()
        self.assertEqual(cm.exception.response, resp)

    def test_response_with(self):
        """Test response modification"""
        resp = Response(
            status_code=200,
            headers={"X-Original": "value"},
            raw_content=b'content',
            request=self.request
        )

        new_resp = resp.WITH(
            headers={"X-New": "value2"}
        )

        self.assertEqual(new_resp.headers["X-New"], "value2")
        self.assertEqual(new_resp.headers["X-Original"], "value")

if __name__ == '__main__':
    unittest.main()
