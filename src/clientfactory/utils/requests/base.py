# ~/ClientFactory/src/clientfactory/utils/requests/base.py
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from loguru import logger as log

@dataclass
class RequestUtilConfig:
    """base configuration for request utilities"""
    delay: float = 0.0 # delay between requests
    timeout: float = 30.0 # request timeout
    retries: int = 3 # max retries
    raiseonerror: bool = False


class RequestUtil(ABC):
    """base class for request utilities"""
    def __init__(self, config: t.Optional[RequestUtilConfig] = None):
        self.config = config or RequestUtilConfig()

    @abstractmethod
    def __enter__(self):
        """context manager entry"""
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """context manager exit"""
        pass
