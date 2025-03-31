# ~/ClientFactory/src/clientfactory/declarative/base.py
"""
Declarative Base Components
---------------------------
Core building blocks for declarative API definition.
Provides base classes and utilities for capturing declarative metadata
and managing class-level configuration.
"""
from __future__ import annotations
import inspect, abc, typing as t, copy as cp
from clientfactory.log import log

class DeclarativeMeta(type):
    """
    Metaclass for declarative components.

    Handles processing of class attributes and inheritance of metadata between declarative classes.
    Enables automatic discovery of declarative components and methods.
    """
    CANTCOPY = (classmethod, staticmethod, property)
    DONTCOPY = {'name'}

    @classmethod
    def _cancopy(mcs, value: t.Any) -> bool:
        """Check if a value can be safely copied"""
        return not isinstance(value, mcs.CANTCOPY)

    def __new__(mcs, name, bases, namespace, **kwargs):
        # create the class to make it referencable
        #log.debug(f"DeclarativeMeta: creating class ({name})")
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        cls.__metadata__ = {}
        ##log.debug(f"DeclarativeMeta: initial metadata: {cls.__metadata__}")

        # Process inheritance first (in reverse order)
        for base in reversed(bases):
            ##log.debug(f"DeclarativeMeta: processing base class ({base.__name__}) for ({name})")
            if hasattr(base, '__metadata__'):
                ##log.debug(f"DeclarativeMeta: base ({base.__name__}) has metadata: {base.__metadata__}")
                for k, v in base.__metadata__.items():
                    if (k not in cls.__metadata__) and (k not in mcs.DONTCOPY):
                        cancopy = mcs._cancopy(v)
                        ##log.debug(f"DeclarativeMeta: copying ({k}) from ({base.__name__}) to ({name}) - cancopy: {cancopy}")
                        cls.__metadata__[k] = (cp.deepcopy(v) if cancopy else v)

        # Process current class attributes
        ##log.debug(f"DeclarativeMeta: processing attributes for ({name})")
        for n, val in namespace.items():
            if (
                not n.startswith('_')
                and
                not callable(val)
                and
                not isinstance(val, type)
                and
                not isinstance(val, property)
            ):
                ##log.debug(f"DeclarativeMeta: processing attribute ({n}) with value ({val}) for ({name})")
                cls.__metadata__[n] = val

        if hasattr(cls, '__declarativetype__'):
            if cls.__declarativetype__ == 'resource':
                cls.__metadata__['name'] = cls.__name__.lower()
                ##log.debug(f"DeclarativeMeta: set resource name ({cls.__metadata__['name']}) for: {name}")

        if hasattr(cls, '_processclassattributes'):
            ##log.debug(f"DeclarativeMeta: calling _processclassattributes for ({name})")
            cls._processclassattributes()
            #log.debug(f"DeclarativeMeta: _processclassattributes completed for ({name})")

        #log.debug(f"DeclarativeMeta: completed creation of ({name}) - metadata: {cls.__metadata__}")
        return cls

class DeclarativeComponent(metaclass=DeclarativeMeta):
    """
    Base class for all declarative components.

    Provides core functionality for declarative API definition:
        - Class attribute discovery and processing
        - Metadata storage and inheritance
        - Runtime configuration and binding

    This class serves as the foundation for declarative resources, clients, and other components in the library.
    """

    __declarativetype__ = 'component'

    @classmethod
    def _processclassattributes(cls) -> None:
        """
        Process class attributes to populate metadata.

        Extracts declarative configuration from class attributes and stores them in the class metadata dictionary.
        """
        pass # handled by DeclarativeMeta.__new__


    @classmethod
    def getmetadata(cls, key: str, default: t.Any = None) -> t.Any:
        """Get metadata value by key with optional default."""
        return cls.__metadata__.get(key, default)

    @classmethod
    def setmetadata(cls, key: str, value: t.Any) -> None:
        """Set metadata value by key"""
        cls.__metadata__[key] = value

    @classmethod
    def hasmetadata(cls, key: str) -> bool:
        """Check if a metadata key exists"""
        return (key in cls.__metadata__)

    @classmethod
    def updatemetdata(cls, updates: dict) -> None:
        """Update metadata with dictionary of values"""
        cls.__metadata__.update(updates)

    @classmethod
    def getallmetadata(cls) -> dict:
        """Get complete metadata dictionary"""
        return cls.__metadata__.copy()

    @classmethod
    def findmetadata(cls, prefix: str) -> dict:
        """Find all metadata entries with keys starting with prefix"""
        return {
            k:v for k,v in cls.__metadata__.items()
            if k.startswith(prefix)
        }

class DeclarativeContainer(DeclarativeComponent):
    """
    Container for declarative components.

    Provides functionality for managing nested declarative components and methods.
    Useful for resources, clients, and other components that can contain nested elements.
    """

    __declarativetype__ = 'container'

    @classmethod
    def _processclassattributes(cls) -> None:
        """
        Process class attributes and discover nested components.

        Extends the base implementation to also cover and process nested declarative components and decorated methods.
        """
        #log.debug(f"DeclarativeContainer: starting attribute processing for ({cls.__name__})")
        #super()._processclassattributes() // No need to call super() since basic processing is in metaclass

        for k in (requiredcontainers:={'components', 'methods'}):
            if k not in cls.__metadata__:
                cls.__metadata__[k] = {}
                ##log.debug(f"DeclarativeContainer: initialized ({k}) container for ({cls.__name__})")

        for name, value in cls.__dict__.items():
            ##log.debug(f"DeclarativeContainer: examining attribute ({name}) on ({cls.__name__})")
            if (name.startswith('__')) and (name.endswith('__')):
                ##log.debug(f"DeclarativeContainer: skipping special attribute ({name})")
                continue # skip special attributes

            # process nested classes
            if (inspect.isclass(value)):
                ##log.debug(f"DeclarativeContainer: found class ({value.__name__}) on ({cls.__name__})")
                if (hasattr(value, '__metadata__')):
                    ##log.debug(f"DeclarativeContainer: class ({value.__name__}) has metadata: {value.__metadata__}")
                    value.setmetadata('parent', cls)
                    componentname = (
                        value.__metadata__.get('name')
                        if value.__metadata__.get('name') is not None
                        else name.lower()
                    )
                    cls.__metadata__['components'][componentname] = value
                    ##log.debug(f"DeclarativeContainer: registered component ({componentname}) on: {cls.__name__}")

            elif callable(value):
                ##log.debug(f"DeclarativeContainer: found callable ({name}) on: {cls.__name__}")
                if hasattr(value, '__declarativemethod__'):
                    cls.__metadata__['methods'][name] = value
                    #log.debug(f"DeclarativeContainer: registered method ({name}) on: {cls.__name__}")

        #log.debug(f"DeclarativeContainer: completed processing for ({cls.__name__}) - metadata: {cls.__metadata__}")


# utilities
def isdeclarative(obj: t.Any) -> bool:
    return (
        inspect.isclass(obj)
        and
        issubclass(obj, DeclarativeComponent)
    )

def getclassmetadata(cls: t.Type) -> dict:
    if hasattr(cls, '__metadata__'):
        return cls.__metadata__.copy()
    return {}

def copymetadata(source: t.Type, target: t.Type, keys: t.Optional[list] = None) -> None:
    """Copy metadata from source to target class."""
    if not hasattr(source, '__metadata__'):
        return

    if not hasattr(target, '__metadata__'):
        target.__metadata__ = {}

    if keys:
        # Only copy the specified keys, REPLACE ALL OTHER METADATA
        target.__metadata__ = {  # <-- This is the fix
            k: cp.deepcopy(source.__metadata__[k])
            for k in keys
            if k in source.__metadata__
        }
    else:
        target.__metadata__.update(cp.deepcopy(source.__metadata__))

    #log.debug(f"copymetadata: Copied metadata from ({source.__name__}) to ({target.__name__})")
