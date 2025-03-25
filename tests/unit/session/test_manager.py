# ~/ClientFactory/tests/unit/session/test_manager.py
"""Tests for state management"""
import pytest
from clientfactory.session.state import StateManager, MemoryStateStore

def test_state_manager_basic():
    """Test basic state manager operations"""
    store = MemoryStateStore()
    manager = StateManager(store=store)

    manager.set("key", "value")
    assert manager.get("key") == "value"

def test_state_manager_autoload():
    """Test state manager autoload"""
    store = MemoryStateStore({"initial": "value"})
    manager = StateManager(store=store, autoload=True)

    assert manager.get("initial") == "value"

def test_state_manager_autosave():
    """Test state manager autosave"""
    store = MemoryStateStore()
    manager = StateManager(store=store, autosave=True)

    manager.set("key", "value")
    loaded = store.load()
    assert loaded["key"] == "value"

def test_state_manager_batch_update():
    """Test state manager batch updates"""
    manager = StateManager(store=MemoryStateStore())

    manager.update({
        "key1": "value1",
        "key2": "value2"
    })

    assert manager.get("key1") == "value1"
    assert manager.get("key2") == "value2"

def test_state_manager_clear():
    """Test state manager clear"""
    store = MemoryStateStore({"key": "value"})
    manager = StateManager(store=store, autoload=True)

    manager.clear()
    assert manager.get("key") is None
    assert store.load() == {}
