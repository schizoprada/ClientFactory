# ~/ClientFactory/tests/unit/session/test_enhanced.py
"""Tests for enhanced session"""
import pytest
from clientfactory.session import (
    EnhancedSession, Headers,
    StateManager, MemoryStateStore
)
from clientfactory.core import SessionConfig

def test_enhanced_session_basic():
    """Test basic enhanced session"""
    session = EnhancedSession()
    assert session is not None

def test_enhanced_session_with_state():
    """Test enhanced session with state management"""
    manager = StateManager(store=MemoryStateStore())
    session = EnhancedSession(statemanager=manager)

    assert session.statemanager is manager

def test_enhanced_session_cookie_persistence():
    """Test cookie persistence"""
    store = MemoryStateStore()
    manager = StateManager(store=store)
    session = EnhancedSession(
        statemanager=manager,
        persistcookies=True
    )

    # Simulate cookie setting
    session._session.cookies.update({"sessionid": "test123"})
    session.close()

    # New session should load cookies
    new_session = EnhancedSession(
        statemanager=manager,
        persistcookies=True
    )
    assert new_session._session.cookies["sessionid"] == "test123"

def test_enhanced_session_config():
    """Test session configuration"""
    config = SessionConfig(
        headers={"User-Agent": "Test/1.0"},
        verify=False
    )
    session = EnhancedSession(config=config)

    assert session._session.headers["User-Agent"] == "Test/1.0"
    assert not session._session.verify
