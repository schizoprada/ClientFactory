# ~/ClientFactory/src/clientfactory/client/__init__.py
"""
Client Module
-------------
This module provides the Client class and related components for building API clients with minimal boilerplate.
"""

from .base import (
    Client, ClientError
)
from .config import (
    ClientConfig
)
from .builder import (
    ClientBuilder
)

from clientfactory.log import log
#log.remove() # remove logging during initialization

__all__ = [
    'Client',
    'ClientError',
    'ClientConfig',
    'ClientBuilder'
]
