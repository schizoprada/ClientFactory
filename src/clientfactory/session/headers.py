# ~/ClientFactory/src/clientfactory/session/headers.py
"""
Header Management
----------------
Utilities for managing session headers with static and dynamic values.
"""
from __future__ import annotations
import typing as t
from clientfactory.log import log

from clientfactory.declarative import DeclarativeComponent

class Headers(DeclarativeComponent):
    """
    Header management with static and dynamic values.

    Can be configured declaratively:
        class MyHeaders(Headers):
            static = {
                "User-Agent": "MyClient/1.0",
                "Accept": "application/json"
            }
            dynamic = {
                "X-Timestamp": lambda: str(int(time.time()))
            }
    """
    __declarativetype__ = 'headers'
    static: dict[str, str] = {}
    dynamic: dict[str, t.Callable[[], str]] = {}

    def __init__(
        self,
        static: t.Optional[dict[str, str]] = None,
        dynamic: t.Optional[dict[str, t.Callable[[], str]]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        if static is not None:
            self.static = static
        if dynamic is not None:
            self.dynamic = dynamic

    def get(self) -> dict[str, str]:
        """Get current headers including dynamic values"""
        headers = self.static.copy()
        headers.update({
            k: v() for k, v in self.dynamic.items()
        })
        return headers

    def update(self, headers: dict[str, str]) -> None:
        """Update static headers"""
        self.static.update(headers)

    def plusdynamic(self, key: str, generator: t.Callable[[], str]) -> None:
        """Add dynamic header generator"""
        self.dynamic[key] = generator
