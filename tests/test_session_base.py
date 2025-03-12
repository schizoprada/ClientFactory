# ~/clientfactory/tests/test_session_base.py 
import unittest
from unittest.mock import Mock, patch
import requests

from session.base import BaseSession, SessionConfig, SessionError
from utils.request import Request, RequestConfig
from utils.response import Response

class TestBaseSession(unittest.TestCase):
    def setUp(self):
        self.session = BaseSession()
        self.test_request = Request(
            method="GET",
            url="http://example.com/test"
        )

    def test_session_initialization(self):
        """Test session initialization with different configs"""
        # Default config
        session = BaseSession()
        self.assertIsNotNone(session._session)

        # Custom config
        config = SessionConfig(
            headers={"User-Agent": "test"},
            cookies={"session": "123"},
            auth=("user", "pass"),
            proxies={"http": "proxy.example.com"},
            verify=False
        )
        session = BaseSession(config)

        # Verify config was applied
        self.assertEqual(session._session.headers["User-Agent"], "test")
        self.assertEqual(session._session.cookies["session"], "123")
        self.assertEqual(session._session.auth, ("user", "pass"))
        self.assertEqual(session._session.proxies["http"], "proxy.example.com")
        self.assertFalse(session._session.verify)

    @patch('requests.Session.send')
    def test_request_execution(self, mock_send):
        """Test basic request execution"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"key": "value"}'
        mock_send.return_value = mock_response

        response = self.session.send(self.test_request)

        # Verify response
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"key": "value"})

        # Verify request was prepared correctly
        args, _ = mock_send.call_args
        prepared_request = args[0]
        self.assertEqual(prepared_request.method, "GET")
        self.assertEqual(prepared_request.url, "http://example.com/test")

    @patch('requests.Session.send')
    def test_retry_behavior(self, mock_send):
        """Test retry behavior on failed requests"""
        # Configure mock to fail twice then succeed
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'success'

        mock_send.side_effect = [
            requests.RequestException("First failure"),
            requests.RequestException("Second failure"),
            mock_response
        ]

        # Configure request with 3 retries
        request = self.test_request.WITH(
            config={'maxretries': 3}
        )

        response = self.session.send(request)
        self.assertEqual(response.content, b'success')
        self.assertEqual(mock_send.call_count, 3)

    @patch('requests.Session.send')
    def test_request_failure(self, mock_send):
        """Test behavior when all retries are exhausted"""
        mock_send.side_effect = requests.RequestException("Persistent failure")

        request = self.test_request.WITH(
            config={'maxretries': 2}
        )

        with self.assertRaises(SessionError) as cm:
            self.session.send(request)

        self.assertEqual(mock_send.call_count, 2)
        self.assertIn("Persistent failure", str(cm.exception))

    def test_context_manager(self):
        """Test session context manager behavior"""
        with patch('requests.Session.close') as mock_close:
            with BaseSession() as session:
                self.assertIsInstance(session, BaseSession)
            mock_close.assert_called_once()

    def test_request_preparation(self):
        """Test request preparation with various configurations"""
        request = Request(
            method="POST",
            url="http://example.com/api",
            headers={"X-Custom": "value"},
            json={"data": "test"}
        )

        prepared = self.session.__prep__(request)

        self.assertEqual(prepared.method, "POST")
        self.assertEqual(prepared.url, "http://example.com/api")
        self.assertEqual(prepared.headers["X-Custom"], "value")
        self.assertEqual(prepared.headers["content-type"], "application/json")

if __name__ == '__main__':
    unittest.main()
