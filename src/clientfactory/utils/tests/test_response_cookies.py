# ~/ClientFactory/src/clientfactory/utils/tests/test_response_cookies.py
import pytest
from dataclasses import dataclass
from clientfactory.utils.response import Response, ResponseError, ExtractionError

# Mock Request class for testing
@dataclass
class MockRequest:
    url: str = "https://api.example.com/endpoint?page=1&limit=10"

@pytest.fixture
def test_response_factory():
    """Helper to create test responses"""
    def _make_response(
        status_code: int = 200,
        headers: dict = None,
        content: bytes = b"",
        url: str = None
    ) -> Response:
        return Response(
            status_code=status_code,
            headers=headers or {},
            raw_content=content,
            request=MockRequest(url=url or "https://api.example.com")
        )
    return _make_response

class TestResponseExtraction:
    def test_string_path_headers(self, test_response_factory):
        response = test_response_factory(
            headers={"X-CSRF-Token": "abc123"}
        )
        assert response.extract(path="headers.x-csrf-token") == "abc123"
        assert response.extract(path="headers.X-CSRF-TOKEN") == "abc123"  # case insensitive
        assert response.extract(path="headers.nonexistent", default="default") == "default"

    def test_iterable_path_headers(self, test_response_factory):
        response = test_response_factory(
            headers={"X-Custom": "value"}
        )
        assert response.extract(path=("headers", "x-custom")) == "value"
        assert response.extract(path=["headers", "X-CUSTOM"]) == "value"

    def test_json_extraction_string(self, test_response_factory):
        response = test_response_factory(
            content=b'{"data": {"items": [{"id": 123}]}}'
        )
        assert response.extract(path="json.data.items[0].id") == 123

    def test_json_extraction_iterable(self, test_response_factory):
        response = test_response_factory(
            content=b'{"data": {"items": [{"id": 123}]}}'
        )
        assert response.extract(path=("json", "data", "items", 0, "id")) == 123

    def test_query_extraction(self, test_response_factory):
        response = test_response_factory(
            url="https://api.example.com/endpoint?page=1&limit=10"
        )
        assert response.extract(path="query.page") == "1"
        assert response.extract(path=("query", "limit")) == "10"

    def test_cookies_extraction(self, test_response_factory):
        response = test_response_factory(
            headers={"Set-Cookie": "sessionid=abc123; Path=/"}
        )
        assert response.extract(path="cookies.sessionid") == "abc123"
        assert response.extract(path=("cookies", "sessionid")) == "abc123"

    def test_default_values(self, test_response_factory):
        response = test_response_factory()
        assert response.extract(path="headers.nonexistent", default="default") == "default"
        assert response.extract(path=("json", "missing"), default=123) == 123
        assert response.extract(path="query.nothing", default=[]) == []

    def test_invalid_source(self, test_response_factory):
        response = test_response_factory()
        assert response.extract(path="invalid.path", default="default") == "default"
        assert response.extract(path=("invalid", "path"), default=None) is None

    def test_complex_json_paths(self, test_response_factory):
        response = test_response_factory(
            content=b'''
            {
                "data": {
                    "items": [
                        {"id": 1, "nested": {"value": "first"}},
                        {"id": 2, "nested": {"value": "second"}}
                    ]
                }
            }
            '''
        )
        assert response.extract(path="json.data.items[1].nested.value") == "second"
        assert response.extract(
            path=("json", "data", "items", 1, "nested", "value")
        ) == "second"

    def test_custom_delimiter(self, test_response_factory):
        response = test_response_factory(
            headers={"X-Custom": "value"}
        )
        assert response.extract(
            path="headers/x-custom",
            delimiter="/",
            default=None
        ) == "value"

    def test_error_handling(self, test_response_factory):
        response = test_response_factory(
            content=b'{"data": {}}'
        )
        # Should return default and log error, not raise
        assert response.extract(
            path="json.data.nonexistent",
            default="default"
        ) == "default"
        assert response.extract(
            path=("json", "data", 0),
            default=None
        ) is None

class TestResponseBasics:
    def test_ok_property(self, test_response_factory):
        assert test_response_factory(status_code=200).ok is True
        assert test_response_factory(status_code=404).ok is False

    def test_bool_conversion(self, test_response_factory):
        assert bool(test_response_factory(status_code=200)) is True
        assert bool(test_response_factory(status_code=500)) is False

    def test_with_updates(self, test_response_factory):
        response = test_response_factory(
            headers={"Original": "value"}
        )
        updated = response.WITH(headers={"New": "value"})
        assert "New" in updated.headers
        assert "Original" in updated.headers
