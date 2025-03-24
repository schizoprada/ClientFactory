# ~/ClientFactory/tests/auth/conftest.py
"""
Global test fixtures and configuration for ClientFactory tests
"""
import os
import sys
import pytest
import requests
import logging
from pathlib import Path

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Global fixtures

@pytest.fixture
def mock_response():
    """Creates a mock requests.Response object with customizable attributes"""

    class MockResponse:
        def __init__(self, status_code=200, content=b'', headers=None, url=None, json_data=None):
            self.status_code = status_code
            self._content = content
            self.headers = headers or {}
            self.url = url or "https://api.example.com/test"
            self._json_data = json_data

        def json(self):
            if self._json_data is not None:
                return self._json_data
            try:
                return json.loads(self._content)
            except:
                raise ValueError("Response content is not valid JSON")

        @property
        def content(self):
            return self._content

        def raise_for_status(self):
            if 400 <= self.status_code < 600:
                raise requests.HTTPError(f"HTTP Error {self.status_code}")

    return MockResponse


@pytest.fixture
def mock_session(monkeypatch):
    """Creates a mock session that doesn't make real HTTP requests"""

    class MockSession:
        def __init__(self, response=None):
            self.response = response or {
                "status_code": 200,
                "content": b'{"status": "ok"}',
                "headers": {"Content-Type": "application/json"},
            }
            self.last_request = None
            self.headers = {}
            self.cookies = {}
            self.proxies = {}
            self.auth = None
            self.verify = True

        def send(self, request, **kwargs):
            self.last_request = request
            return requests.Response()

        def prepare_request(self, request):
            class PreparedRequest:
                def __init__(self, request):
                    self.method = request.method
                    self.url = request.url
                    self.headers = request.headers
                    self.body = request.data or request.json

            return PreparedRequest(request)

        def close(self):
            pass

    session = MockSession()

    # Patch requests.Session to return our mock
    monkeypatch.setattr(requests, "Session", lambda: session)

    return session


@pytest.fixture
def api_server_url():
    """Returns the URL to a test API server, from environment or default"""
    return os.environ.get("TEST_API_URL", "https://httpbin.org")
