# ~/ClientFactory/src/clientfactory/session/enhanced.py
"""
Enhanced Session
---------------
Session implementation with state management and additional features
"""
from __future__ import annotations
import typing as t
from loguru import logger as log

from clientfactory.core import Session, SessionConfig, Request, Response
from clientfactory.declarative import DeclarativeComponent
from clientfactory.session.state.manager import StateManager

class EnhancedSession(Session):
    """
    Session with state management and enhanced features.

    Can be configured declaratively:
        class MySession(EnhancedSession):
            statemanager = MyStateManager
            headers = {"User-Agent": "MyClient/1.0"}
            persistcookies = True
    """
    __declarativetype__ = 'session'
    statemanager: t.Optional[StateManager] = None
    persistcookies: bool = False

    def __init__(
        self,
        config: t.Optional[SessionConfig] = None,
        statemanager: t.Optional[StateManager] = None,
        persistcookies: t.Optional[bool] = None,
        **kwargs
    ):
        """Initialize enhanced session"""
        super().__init__(config, **kwargs)

        if statemanager is not None:
            self.statemanager = statemanager
        if persistcookies is not None:
            self.persistcookies = persistcookies

        # Load persisted cookies if any
        if self.persistcookies and self.statemanager:
            cookies = self.statemanager.get('cookies', {})
            if cookies:
                self._session.cookies.update(cookies)

    def send(self, request: Request) -> Response:
        """Send request and handle cookie persistence"""
        response = super().send(request)

        # Persist cookies if enabled
        if self.persistcookies and self.statemanager:
            self.statemanager.set('cookies', dict(self._session.cookies))

        return response

    def close(self) -> None:
        """Close session and save state"""
        if self.persistcookies and self.statemanager:
            if (cookies:={k:v for k,v in self._session.cookies.items()}):
                self.statemanager.set('cookies', cookies)
        super().close()
