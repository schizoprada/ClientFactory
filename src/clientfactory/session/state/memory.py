# ~/ClientFactory/src/clientfactory/session/state/memory.py
"""
Memory-based State Storage
-------------------------
Implements in-memory state storage for temporary or testing use.
"""
from __future__ import annotations
import typing as t
from clientfactory.log import log

from clientfactory.session.state.base import StateStore, StateError

class MemoryStateStore(StateStore):
    """
    In-memory state storage.

    Stores state in memory without persistence. Useful for:
    - Temporary storage
    - Testing
    - Scenarios where persistence isn't needed
    """
    __declarativetype__ = 'memorystore'
    format = "memory"

    def __init__(self, initialstate: t.Optional[dict] = None, path: t.Optional[str] = None):
        super().__init__(path)
        self._state = (initialstate or {}).copy()

    def load(self) -> dict:
        """Load state from memory"""
        return self._state.copy()

    def save(self, state: dict) -> None:
        """Save state to memory"""
        self._state = state.copy()

    def clear(self) -> None:
        """Clear stored state"""
        self._state.clear()

    def update(self, state: dict) -> None:
        """Update stored state with new values"""
        self._state.update(state)

    @property
    def current(self) -> dict:
        """Get current state without copying"""
        return self._state
