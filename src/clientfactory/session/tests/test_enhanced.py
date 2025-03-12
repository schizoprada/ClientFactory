# ~/ClientFactory/src/clientfactory/session/tests/test_enhanced.py
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from clientfactory.session.enhanced import EnhancedSession
from clientfactory.session.headers import Headers
from clientfactory.session.cookies import CookieManager, Cookie
from clientfactory.session.state import StateManager, FileStateStore
from clientfactory.utils import Request, Response, RequestMethod

class TestEnhancedSession:
    def test_initialization(self):
        session = EnhancedSession()
        assert isinstance(session.headers, Headers)
        assert isinstance(session.cookies, CookieManager)
        assert session.state is None

    def test_request_preparation(self):
        session = EnhancedSession(
            headers=Headers(static={"User-Agent": "test"}),
            cookies=CookieManager(static={"session": "abc123"})
        )

        request = Request(
            method=RequestMethod.GET,
            url="https://example.com"
        )

        prepared = session.__prep__(request)
        assert prepared.headers["User-Agent"] == "test"
        assert prepared.cookies["session"].value == "abc123"  # Compare the value attribute
        ## CONSIDER:: WHETHER WE SHOULD MAKE IT SO THAT U DONT HAVE TO ACCESS .VALUE ##
    @patch('clientfactory.session.base.BaseSession.send')
    def test_response_handling(self, mock_send):
        # Mock response with cookies
        mock_response = Mock()
        mock_response.cookies = {"newsession": "xyz789"}
        mock_response.headers = {}
        mock_response.status_code = 200
        mock_response.content = b""
        mock_send.return_value = Response(
            status_code=200,
            headers={},
            raw_content=b"",
            request=Request(method=RequestMethod.GET, url="https://example.com")
        )

        session = EnhancedSession(
            cookies=CookieManager()
        )

        response = session.send(Request(
            method=RequestMethod.GET,
            url="https://example.com"
        ))

        assert mock_send.called

    def test_initial_request(self):
        with patch('clientfactory.session.base.BaseSession.send') as mock_send:
            # Mock response with extractable data
            mock_response = Response(
                status_code=200,
                headers={"x-csrf-token": "token123"},
                raw_content=b"",
                request=Request(method=RequestMethod.GET, url="https://example.com")
            )
            mock_send.return_value = mock_response

            session = EnhancedSession(
                state=StateManager()
            )

            # The extract parameter will be handled separately in initialrequest
            response = session.initialrequest(
                "https://example.com",
                extract={
                    "csrf_token": "headers.x-csrf-token"
                }
            )

            assert session.state.state.metadata.get("csrf_token") == "token123"
            assert mock_send.called
