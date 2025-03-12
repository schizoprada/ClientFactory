# ~/ClientFactory/src/clientfactory/session/tests/test_base.py
import pytest
import tempfile
import requests as rq
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from clientfactory.session.base import BaseSession, SessionConfig, SessionError
from clientfactory.utils import Request, RequestMethod

class TestBaseSession:
    def test_basic_config(self):
        config = SessionConfig(
            headers={"User-Agent": "test"},
            cookies={"session": "abc123"}
        )
        session = BaseSession(config=config)
        assert session._session.headers["User-Agent"] == "test"
        assert session._session.cookies["session"] == "abc123"

    def test_state_management(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                persist=True,
                storepath=str(Path(tmpdir) / "session.json")
            )
            session = BaseSession(config=config)

            # Mock the response
            with patch('requests.Session.send') as mock_send:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.headers = {}
                mock_resp.content = b""
                mock_send.return_value = mock_resp

                # Test state tracking
                with session:
                    response = session.send(Request(
                        method=RequestMethod.GET,
                        url="https://example.com"
                    ))
                    assert session.state.lastrequest is not None
                    assert session.state.failedattempts == 0

    def test_error_tracking(self):
        session = BaseSession(config=SessionConfig())
        with patch('requests.Session.send') as mock_send:
            mock_send.side_effect = rq.RequestException("Network error")

            with pytest.raises(SessionError):
                session.send(Request(
                    method=RequestMethod.GET,
                    url="https://example.com"
                ))
            assert session.state.failedattempts > 0

    def test_context_manager(self):
        session = BaseSession()
        with session as s:
            assert isinstance(s, BaseSession)
            # Session is automatically closed after context
