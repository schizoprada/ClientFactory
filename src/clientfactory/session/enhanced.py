# ~/ClientFactory/src/clientfactory/session/enhanced.py
"""
Enhanced Session
---------------
Session implementation with state management and additional features
"""
from __future__ import annotations
import inspect, typing as t
from clientfactory.log import log

from clientfactory.core import Session, SessionConfig, Request, Response
from clientfactory.auth import BaseAuth
from clientfactory.declarative import DeclarativeComponent
from clientfactory.session.headers import Headers
from clientfactory.session.state.manager import StateManager

class EnhancedSession(Session):
    """
    Session with state management and enhanced features.

    Can be configured declaratively:
        class MySession(EnhancedSession):
            statemanager = MyStateManager
            headers = {"User-Agent": "MyClient/1.0"}
            cookies = {"session_id": "abc123"}
            persistcookies = True
    """
    __declarativetype__ = 'session'
    statemanager: t.Optional[StateManager] = None
    persistcookies: bool = False
    cookies: t.Optional[dict] = None

    def __init__(
            self,
            config: t.Optional[SessionConfig] = None,
            auth: t.Optional[BaseAuth] = None,
            statemanager: t.Optional[StateManager] = None,
            headers: t.Optional[Headers] = None,
            cookies: t.Optional[dict] = None,
            persistcookies: t.Optional[bool] = None,
            **kwargs
        ):
        """Initialize enhanced session"""
        log.info(f"DEBUGGING ENHANCED SESSION INIT - Received auth: {auth}")
        from clientfactory.utils.internal.attribution import attributes
        sources = [self, self.__class__]

        # 1. create config if not provided
        if not config:
            config = SessionConfig()

        # 2. resolve headers from class attribute if not provided
        if headers is None:
            headers = attributes.resolve('headers', sources)
            if headers is not None:
                log.info(f"EnhancedSession: resolved headers from attributes ({headers.__class__.__name__}): {headers}")
            else:
                log.warning(f"EnhancedSession: failed to resolve headers from attributes from sources: {sources}")

        # 3. apply headers if available
        if headers is not None:
            if inspect.isclass(headers):
                headers = headers()
                log.info(f"EnhancedSession: instantiated headers ({headers.__class__.__name__})")

            if hasattr(headers, 'static'):
                config.headers.update(headers.static)
                log.info(f"EnhancedSession: updated config headers: {config.headers}")

        # 4. resolve auth
        if auth is None:
            auth = attributes.resolve('auth', sources)
            if auth is not None:
                log.info(f"EnhancedSession: resolved auth from attributes ({auth.__class__.__name__}): {auth}")
            else:
                log.warning(f"EnhancedSession: failed to resolve auth from attributes from sources: {sources}")

        # 5. instantiate auth if its a class
        if (auth is not None) and inspect.isclass(auth):
            auth = auth()
            log.info(f"EnhancedSession: instantiated auth ({auth.__class__.__name__})")

        # 6. initialize base session
        super().__init__(config, auth, **kwargs)
        log.info(f"DEBUGGING ENHANCED SESSION INIT - Base Session initialized, self.auth: {self.auth}")

        # 7. resolve remaining attributes
        remainingattrs = attributes.collect(
            self,
            ['statemanager', 'persistcookies', 'cookies'],
            includemetadata=True,
            includeconfig=False,
            includeparent=False,
            silent=False
        )

        log.debug(f"EnhancedSession: collected remaining attributes: {remainingattrs}")

        # 8. override with explicit parameters
        if statemanager is not None:
            log.info(f"EnhancedSession: overriding resolved statemanager ({remainingattrs.get('statemanager')}) with provided parameter: {statemanager}")
            remainingattrs['statemanager'] = statemanager
        if persistcookies is not None:
            log.info(f"EnhancedSession: overriding resolved persistcookies ({remainingattrs.get('persistcookies')}) with provided parameter: {persistcookies}")
            remainingattrs['persistcookies'] = persistcookies
        if cookies is not None:
            log.info(f"EnhancedSession: overriding resolved cookies ({remainingattrs.get('cookies')}) with provided parameter: {cookies}")
            remainingattrs['cookies'] = cookies

        # 9. instantiate statemanager if necessary
        if ('statemanager' in remainingattrs):
            if inspect.isclass(remainingattrs['statemanager']):
                try:
                    statemanagercls = remainingattrs['statemanager']

                    statestore = None
                    storeattr = attributes.resolve('store', [statemanagercls])
                    if storeattr:
                        log.info(f"EnhancedSession: resolved statestore ({storestore.__class__.__name__}) from StateManager class: {statemanagercls.__class__.__name__}")
                        if inspect.isclass(storeattr):
                            try:
                                statestore = storeattr()
                                log.info(f"EnhancedSession: instantiated store ({statestore.__class__.__name__}) for statemanager")
                            except Exception as e:
                                log.error(f"EnhancedSession: failed to instantiate store for statemanager: {e}")
                                statestore = None
                        else:
                            statestore = storeattr

                    if statestore:
                        remainingattrs['statemanager'] = statemanagercls(store=statestore)
                    else:
                        remainingattrs['statemanager'] = statemanagercls()

                    log.info(f"EnhancedSession: instantiated statemanager ({remainingattrs['statemanager'].__class__.__name__})")
                except Exception as e:
                    log.error(f"EnhancedSession: failed to instantiate statemanager: {e}")
                    remainingattrs['statemanager'] = None

        # 10. set remaining attributes on self
        for k, v in remainingattrs.items():
            setattr(self, k, v)

        # 11. load persisted cookies if any
        if getattr(self, 'persistcookies', False) and (hasattr(self, 'statemanager')) and (self.statemanager):
            cookies = self.statemanager.get('cookies', {})
            if cookies:
                self._session.cookies.update(cookies)
                log.info(f"EnhancedSession: persistent cookies loaded from statemanager: {cookies}")

        # 12. apply cookies if available
        if hasattr(self, 'cookies') and self.cookies:
            self._session.cookies.update(self.cookies)
            log.info(f"EnhancedSession: applied cookies from attributes: {self.cookies}")

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
