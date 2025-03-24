# ~/ClientFactory/tests/unit/test_session.py
"""
Tests for the core.session module
"""
import pytest
from unittest.mock import MagicMock, patch, call

from clientfactory.core.session import (
    Session, SessionConfig, SessionError,
    SessionBuilder
)
from clientfactory.core.request import Request, RequestMethod
from clientfactory.core.response import Response


@pytest.fixture
def mock_requests_session():
    """Create a mock for the requests.Session"""
    with patch('requests.Session') as mock_class:
        # Create a session instance with the required attributes
        session_instance = MagicMock()
        session_instance.headers = MagicMock()
        session_instance.cookies = MagicMock()
        session_instance.proxies = MagicMock()

        # Configure return value for the class
        mock_class.return_value = session_instance

        yield session_instance



def test_session_initialization():
    """Test session initialization with different configurations"""
    # Basic initialization
    session = Session()
    assert isinstance(session.config, SessionConfig)

    # Configuration with properties
    config = SessionConfig(
        headers={"User-Agent": "ClientFactory/1.0"},
        cookies={"session": "abc123"},
        maxretries=5
    )
    session = Session(config=config)
    assert session.config == config

    # With auth
    auth = MagicMock()
    session = Session(config=config, auth=auth)
    assert session.auth == auth


# Fix for test_session_create_session:
def test_session_create_session():
    """Test the creation of the underlying requests session"""
    # Create config
    config = SessionConfig(
        headers={"User-Agent": "ClientFactory/1.0"},
        cookies={"session": "abc123"},
        proxies={"http": "http://proxy.example.com"},
        verify=False,
        maxretries=3
    )

    # Use patch directly in the test
    with patch('requests.Session') as mock_session_class:
        # Create mock session instance
        mock_session = MagicMock()
        mock_session.headers = MagicMock()
        mock_session.cookies = MagicMock()
        mock_session.proxies = MagicMock()

        # Set return value
        mock_session_class.return_value = mock_session

        # Create the session
        session = Session(config=config)

        # Verify the mocks were called
        mock_session.headers.update.assert_called_with({"User-Agent": "ClientFactory/1.0"})
        mock_session.cookies.update.assert_called_with({"session": "abc123"})
        mock_session.proxies.update.assert_called_with({"http": "http://proxy.example.com"})
        assert mock_session.verify == False


def test_session_hooks():
    """Test adding request and response hooks"""
    session = Session()

    # Add request hook
    request_hook = MagicMock(return_value=MagicMock(spec=Request))
    session.addrequesthook(request_hook)
    assert request_hook in session._requesthooks

    # Add response hook
    response_hook = MagicMock(return_value=MagicMock(spec=Response))
    session.addresponsehook(response_hook)
    assert response_hook in session._responsehooks


def test_session_prepare_request():
    """Test request preparation process"""
    # Create session with auth
    auth = MagicMock()
    auth.prepare.return_value = MagicMock(spec=Request)

    # Mock requests.Session with proper attributes
    with patch('requests.Session', autospec=True) as mock_session_class:
        mock_session = MagicMock()
        mock_session.headers = {}
        mock_session.cookies = {}
        mock_session_class.return_value = mock_session

        session = Session(auth=auth)

        # Add request hook
        request_hook = MagicMock(side_effect=lambda req: req)
        session.addrequesthook(request_hook)

        # Create request
        request = MagicMock(spec=Request)
        request.prepare.return_value = request
        request.method = RequestMethod.GET
        request.url = "https://api.example.com/test"
        request.params = {}
        request.headers = {}
        request.cookies = {}
        request.json = None
        request.data = None
        request.files = None

        # Prepare request
        with patch('requests.Request', autospec=True) as mock_request:
            result = session.preparerequest(request)

            # Check request hook was called
            request_hook.assert_called_once_with(request)

            # Check auth was applied
            auth.prepare.assert_called_once()


@patch('requests.Session')
def test_session_send(mock_session_class):
    """Test sending a request"""
    # Create mock session instance
    mock_session = MagicMock()
    mock_session.headers = MagicMock()
    mock_session.cookies = MagicMock()

    # Configure response
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true}'
    response.headers = {"Content-Type": "application/json"}

    # Set up return values
    mock_session.send.return_value = response
    mock_session.prepare_request.return_value = MagicMock()
    mock_session_class.return_value = mock_session

    # Create session
    session = Session()

    # Create request with properly mocked config
    request = MagicMock(spec=Request)
    # Add config attribute
    request.config = MagicMock()
    request.config.timeout = 30.0
    request.config.allowredirects = True
    request.config.stream = False

    request.prepare.return_value = request
    request.method = RequestMethod.GET
    request.url = "https://api.example.com/test"
    request.params = {}
    request.headers = {}
    request.cookies = {}
    request.json = None
    request.data = None
    request.files = None

    # Send request
    result = session.send(request)

    # Verify request was sent
    assert mock_session.send.called
    assert isinstance(result, Response)


def test_session_context_manager():
    """Test using session as a context manager"""
    # Create session
    session = Session()
    session.close = MagicMock()

    # Use as context manager
    with session as s:
        assert s is session

    # Check close was called
    session.close.assert_called_once()


def test_session_builder():
    """Test session builder functionality"""
    # Create builder
    builder = SessionBuilder()

    # Configure session
    builder.headers({"User-Agent": "ClientFactory/1.0"})
    builder.cookies({"session": "abc123"})
    builder.proxies({"http": "http://proxy.example.com"})
    builder.verify(False)
    builder.maxretries(5)

    # Add auth
    auth = MagicMock()
    builder.auth(auth)

    # Add hooks
    request_hook = MagicMock()
    response_hook = MagicMock()
    builder.requesthook(request_hook)
    builder.responsehook(response_hook)

    # Build session
    session = builder.build()

    # Check configuration
    assert session.config.headers == {"User-Agent": "ClientFactory/1.0"}
    assert session.config.cookies == {"session": "abc123"}
    assert session.config.proxies == {"http": "http://proxy.example.com"}
    assert session.config.verify == False
    assert session.config.maxretries == 5

    # Check auth
    assert session.auth == auth

    # Check hooks
    assert request_hook in session._requesthooks
    assert response_hook in session._responsehooks
