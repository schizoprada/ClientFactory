# ~/ClientFactory/src/clientfactory/session/state/manager.py
"""
State Management
---------------
Manages session state persistence and access
"""
from __future__ import annotations
import inspect, typing as t
from clientfactory.log import log

from clientfactory.declarative import DeclarativeComponent
from clientfactory.session.state.base import StateStore, StateError

class StateManager(DeclarativeComponent):
    """
    Manages session state persistence.

    Can be configured declaratively:
        class MyManager(StateManager):
            store = MyJSONStore
            autoload = True
            autosave = True
    """
    __declarativetype__ = 'statemanager'
    store: t.Optional[StateStore] = None
    autoload: bool = True
    autosave: bool = True

    def __init__(
        self,
        store: t.Optional[StateStore] = None,
        autoload: t.Optional[bool] = None,
        autosave: t.Optional[bool] = None
    ):
        """Initialize state manager"""
        from clientfactory.utils.internal import attributes
        sources = [self, self.__class__]

        if store is None:
            store = attributes.resolve('store', sources)
            log.info(f"StateManager: store resolved from sources: {store}")
        if autoload is None:
            autoload = attributes.resolve('autoload', sources, default=True)
            log.info(f"StateManager: autoload resolved from sources: {autoload}")
        if autosave is None:
            autosave = attributes.resolve('autosave', sources, default=True)
            log.info(f"StateManager: autosave resolved from sources: {autosave}")

        self.autoload = autoload
        self.autosave = autosave
        self._state = {}

        if (store is not None) and inspect.isclass(store):
            try:
                store = store()
                log.info(f"StateManager: instantiated store ({store.__class__.__name__})")
            except Exception as e:
                log.error(f"StateManager: error instantiating store: {e}")
                store = None
        self.store = store

        if self.store and self.autoload:
            try:
                self.load()
            except Exception as e:
                log.error(f"StateManager: failed to load initial state: {e}")

    def load(self) -> None:
        """Load state from storage"""
        if not self.store:
            raise StateError("No state store configured")
        try:
            self._state = self.store.load()
            log.debug(f"Loaded state from {self.store.__class__.__name__}")
        except Exception as e:
            log.error(f"Failed to load state: {e}")
            raise StateError(f"Failed to load state: {e}")

    def save(self) -> None:
        """Save current state"""
        if not self.store:
            raise StateError("No state store configured")
        try:
            self.store.save(self._state)
            log.debug(f"Saved state to {self.store.__class__.__name__}")
        except Exception as e:
            log.error(f"Failed to save state: {e}")
            raise StateError(f"Failed to save state: {e}")

    def clear(self) -> None:
        """Clear current state"""
        self._state = {}
        if self.store and self.autosave:
            self.store.clear()
            log.debug("Cleared state")

    def get(self, key: str, default: t.Any = None) -> t.Any:
        """Get value from state"""
        return self._state.get(key, default)

    def set(self, key: str, value: t.Any) -> None:
        """Set value in state"""
        self._state[key] = value
        if self.store and self.autosave:
            self.save()

    def update(self, values: dict) -> None:
        """Update multiple values in state"""
        self._state.update(values)
        if self.store and self.autosave:
            self.save()

    def remove(self, key: str) -> None:
        """Remove key from state"""
        self._state.pop(key, None)
        if self.store and self.autosave:
            self.save()
