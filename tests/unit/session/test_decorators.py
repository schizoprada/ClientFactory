# ~/ClientFactory/tests/unit/session/test_decorators.py
"""Tests for session decorators"""
import pytest
from clientfactory.decorators.session import (
    statestore, jsonstore, picklestore, memorystore,
    statemanager, headers, enhancedsession
)
from clientfactory.decorators.session import headers

def test_statestore_decorator():
    """Test basic state store decorator"""
    @statestore(path="test.dat")
    class TestStore:
        pass

    assert TestStore.path == "test.dat"

def test_jsonstore_decorator(tmp_path):
    """Test JSON store decorator"""
    @jsonstore(path="test.json")
    class TestStore:
        pass

    store = TestStore()
    assert store.path == "test.json"
    assert store.format == "json"

def test_picklestore_decorator(tmp_path):
    """Test pickle store decorator"""
    @picklestore(path="test.pkl")
    class TestStore:
        pass

    store = TestStore()
    assert store.path == "test.pkl"
    assert store.format == "pickle"

def test_memorystore_decorator():
    """Test memory store decorator"""
    initial = {"key": "value"}

    @memorystore(initial=initial)
    class TestStore:
        pass

    store = TestStore()
    assert store.load() == initial

def test_statemanager_decorator():
    """Test state manager decorator"""
    @memorystore
    class TestStore:
        pass

    @statemanager(store=TestStore())
    class TestManager:
        pass

    manager = TestManager()
    assert manager.store is not None
    assert manager.autoload is True

def test_headers_decorator():
    """Test headers decorator"""
    @headers(static={"User-Agent": "Test/1.0"})
    class TestHeaders:
        pass

    headers = TestHeaders()
    assert headers.get()["User-Agent"] == "Test/1.0"

def test_enhancedsession_decorator():
    """Test enhanced session decorator"""
    @memorystore
    class TestStore:
        pass

    @statemanager(store=TestStore())
    class TestManager:
        pass

    @enhancedsession(statemanager=TestManager())
    class TestSession:
        pass

    session = TestSession()
    assert session.statemanager is not None
    assert session.persistcookies is False
