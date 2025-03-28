# ~/ClientFactory/src/clientfactory/session/state/base.py
"""
Base State Storage Interface
---------------------------
Defines the interface for session state storage implementations.
"""
from __future__ import annotations
import abc, typing as t
from clientfactory.log import log

from clientfactory.declarative import DeclarativeComponent

class StateError(Exception):
    """Base exception for state-related errors"""
    pass

class StateStore(DeclarativeComponent):
    """
    Base class for state storage implementations.

    Can be used declaratively:
        @statestore
        class MyStore(StateStore):
            path = "mystate.json"
            format = "json"
    """
    __declarativetype__ = 'statestore'
    path: str = ""
    format: str = "json"

    def __init__(self, path: t.Optional[str] = None, **kwargs):
        if path is not None:
            self.path = path
        #super().__init__(**kwargs)

    @abc.abstractmethod
    def load(self) -> dict:
        """Load state from storage"""
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, state: dict) -> None:
        """Save state to storage"""
        raise NotImplementedError

    @abc.abstractmethod
    def clear(self) -> None:
        """Clear stored state"""
        raise NotImplementedError
