# ~/ClientFactory/src/clientfactory/session/__init__.py
"""
Session Management
----------------
Enhanced session handling with state management and header utilities.
"""
from .enhanced import EnhancedSession
from .headers import Headers
from .state import (
    StateStore, StateError,
    FileStateStore, JSONStateStore, PickleStateStore,
    MemoryStateStore, StateManager
)

__all__ = [
    'EnhancedSession',
    'Headers',
    'StateStore',
    'StateError',
    'FileStateStore',
    'JSONStateStore',
    'PickleStateStore',
    'MemoryStateStore',
    'StateManager'
]
