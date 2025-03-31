# ~/ClientFactory/src/clientfactory/decorators/session.py
"""
Session Management Decorators
---------------------------
Decorators for defining session management components in a declarative way.
"""
from __future__ import annotations
import typing as t
from clientfactory.log import log

from clientfactory.core.session import Session, SessionConfig
from clientfactory.session.state.base import StateStore
from clientfactory.session.state.file import FileStateStore, JSONStateStore, PickleStateStore
from clientfactory.session.state.memory import MemoryStateStore
from clientfactory.session.state.manager import StateManager
from clientfactory.session.headers import Headers

def statestore(cls=None, *, path: t.Optional[str] = None, format: t.Optional[str] = None):
    """
    Base decorator for state stores.

    Can be used with or without arguments:
        @statestore
        class MyStore:
            path = "mystate.json"

        @statestore(path="state.json", format="json")
        class MyStore:
            pass
    """
    metadata = {}
    if path is not None:
        metadata['path'] = path
    if format is not None:
        metadata['format'] = format

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, StateStore):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
                if hasattr(cls, k):
                    setattr(cls, k, v)
            return cls

        namespace = dict(cls.__dict__)
        if path is not None:
            namespace['path'] = path
        if format is not None:
            namespace['format'] = format

        bases = (StateStore,) + cls.__bases__
        newcls = type(cls.__name__, bases, namespace)

        for k, v in metadata.items():
            newcls.setmetadata(k, v)

        log.debug(f"statestore: converted ({cls.__name__}) to declarative state store")
        return newcls

    return decorator if cls is None else decorator(cls)

def jsonstore(cls=None, *, path: t.Optional[str] = None):
    """JSON-specific state store decorator"""
    def decorator(cls):
        if path is not None:
            if isinstance(cls, type) and issubclass(cls, JSONStateStore):
                cls.path = path
                cls.setmetadata('path', path)
                return cls
            return type(cls.__name__, (JSONStateStore,), {'path': path})
        if isinstance(cls, type):
            return type(cls.__name__, (JSONStateStore,), dict(cls.__dict__))
        return JSONStateStore
    return decorator if cls is None else decorator(cls)

def picklestore(cls=None, *, path: t.Optional[str] = None):
    """Pickle-specific state store decorator"""
    def decorator(cls):
        if path is not None:
            if isinstance(cls, type) and issubclass(cls, PickleStateStore):
                cls.path = path
                cls.setmetadata('path', path)
                return cls
            return type(cls.__name__, (PickleStateStore,), {'path': path})
        if isinstance(cls, type):
            return type(cls.__name__, (PickleStateStore,), dict(cls.__dict__))
        return PickleStateStore
    return decorator if cls is None else decorator(cls)

def memorystore(cls=None, *, initial: t.Optional[dict] = None):
    """Memory-specific state store decorator"""
    def decorator(cls):
        if initial is not None:
            if isinstance(cls, type) and issubclass(cls, MemoryStateStore):
                cls._state = initial.copy()
                return cls

            # Create a new class that properly initializes the state
            def __init__(self, *args, **kwargs):
                super(type(self), self).__init__(*args, **kwargs)
                self._state = initial.copy()

            namespace = {'__init__': __init__}
            if isinstance(cls, type):
                namespace.update(dict(cls.__dict__))

            newcls = type(cls.__name__, (MemoryStateStore,), namespace)
            return newcls

        if isinstance(cls, type):
            return type(cls.__name__, (MemoryStateStore,), dict(cls.__dict__))
        return MemoryStateStore
    return decorator if cls is None else decorator(cls)

def statemanager(cls=None, *, store: t.Optional[StateStore] = None, autoload: bool = True, autosave: bool = True):
    """
    Decorator for state managers.

    Can be used with or without arguments:
        @statemanager
        class MyManager:
            store = MyStore

        @statemanager(store=MyStore(), autoload=True)
        class MyManager:
            pass
    """
    metadata = {
        'autoload': autoload,
        'autosave': autosave
    }
    if store is not None:
        metadata['store'] = store

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, StateManager):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
                if hasattr(cls, k):
                    setattr(cls, k, v)
            return cls

        namespace = dict(cls.__dict__)
        namespace.update(metadata)

        bases = (StateManager,) + cls.__bases__
        newcls = type(cls.__name__, bases, namespace)

        for k, v in metadata.items():
            newcls.setmetadata(k, v)

        log.debug(f"statemanager: converted ({cls.__name__}) to state manager")
        return newcls

    return decorator if cls is None else decorator(cls)

def headers(cls=None, *, static: t.Optional[dict] = None, dynamic: t.Optional[dict] = None):
    """
    Decorator for header configurations.

    Can be used with or without arguments:
        @headers
        class MyHeaders:
            static = {"User-Agent": "MyClient/1.0"}

        @headers(static={"Accept": "application/json"})
        class MyHeaders:
            pass
    """
    metadata = {}
    if static is not None:
        metadata['static'] = static
    if dynamic is not None:
        metadata['dynamic'] = dynamic

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, Headers):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
                if hasattr(cls, k):
                    setattr(cls, k, v)
            return cls

        namespace = dict(cls.__dict__)
        namespace.update(metadata)

        bases = (Headers,) + cls.__bases__
        newcls = type(cls.__name__, bases, namespace)

        for k, v in metadata.items():
            newcls.setmetadata(k, v)

        log.debug(f"headers: converted ({cls.__name__}) to headers configuration")
        return newcls

    return decorator if cls is None else decorator(cls)

# ~/ClientFactory/src/clientfactory/decorators/session.py (update)

def session(cls=None, **kwargs):
    """
    Decorator for session configuration.

    Allows defining session configuration as a class:

    @session
    class MySession:
        headers = {"User-Agent": "Custom"}
        cookies = {"session_id": "123"}
    """
    def decorator(cls):
        from clientfactory.core.session import Session

        # Create a new class with Session as base
        newcls = type(cls.__name__, (Session,), dict(cls.__dict__))

        # Apply any kwargs passed to the decorator
        for k, v in kwargs.items():
            newcls.setmetadata(k, v)
            setattr(newcls, k, v)

        return newcls

    return decorator if cls is None else decorator(cls)


def enhancedsession(cls=None, *, statemanager: t.Optional[StateManager] = None, headers: t.Optional[Headers] = None, persistcookies: bool = False):
    """
    Decorator for enhanced sessions.

    Can be used with or without arguments:
        @enhancedsession
        class MySession:
            statemanager = MyManager
            persistcookies = True

        @enhancedsession(statemanager=MyManager(), headers=MyHeaders())
        class MySession:
            pass
    """
    from clientfactory.session.enhanced import EnhancedSession
    metadata = {'persistcookies': persistcookies}
    if statemanager is not None:
        metadata['statemanager'] = statemanager
    if headers is not None:
        metadata['headers'] = headers

    log.info(f"enhancedsession: metadata before decorator call: {metadata}")
    def decorator(cls):
        # Create new class with EnhancedSession as base
        newcls = type(cls.__name__, (EnhancedSession,), dict(cls.__dict__))

        # Apply metadata directly as attributes
        for k, v in metadata.items():
            setattr(newcls, k, v)

        return newcls

    return decorator if cls is None else decorator(cls)
