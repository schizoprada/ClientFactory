# ~/ClientFactory/tests/unit/session/test_state.py
"""Tests for state storage implementations"""
import pytest
import os
from clientfactory.session.state import (
    StateStore, StateError,
    JSONStateStore, PickleStateStore, MemoryStateStore
)

def test_memory_store_basic():
    """Test basic memory store operations"""
    store = MemoryStateStore()
    test_state = {"key": "value"}

    store.save(test_state)
    loaded = store.load()

    assert loaded == test_state
    assert loaded is not test_state  # Should be a copy

def test_memory_store_initial_state():
    """Test memory store with initial state"""
    initial = {"initial": "value"}
    store = MemoryStateStore(initialstate=initial)

    loaded = store.load()
    assert loaded == initial
    assert loaded is not initial

def test_json_store(tmp_path):
    """Test JSON store operations"""
    filepath = tmp_path / "test.json"
    store = JSONStateStore(str(filepath))
    test_state = {"key": "value"}

    store.save(test_state)
    assert filepath.exists()

    loaded = store.load()
    assert loaded == test_state

def test_pickle_store(tmp_path):
    """Test pickle store operations"""
    filepath = tmp_path / "test.pkl"
    store = PickleStateStore(str(filepath))
    test_state = {"key": "value"}

    store.save(test_state)
    assert filepath.exists()

    loaded = store.load()
    assert loaded == test_state

def test_store_clear():
    """Test store clear operation"""
    store = MemoryStateStore({"key": "value"})
    store.clear()
    assert store.load() == {}

def test_store_invalid_path():
    """Test store with invalid path"""
    store = JSONStateStore("/invalid/path/test.json")
    with pytest.raises(StateError):
        store.save({"key": "value"})
