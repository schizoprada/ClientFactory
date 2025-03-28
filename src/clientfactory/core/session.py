# ~/ClientFactory/src/clientfactory/core/session.py
"""
Session Class
-------------
Defines the core Session class for executing HTTP requests.
The Session handles authentication, request execution, and maintains state.
"""
from __future__ import annotations
import typing as t, requests as rq
from dataclasses import dataclass, field
from contextlib import AbstractContextManager
import urllib.parse
from clientfactory.log import log

from clientfactory.core.request import Request, RequestConfig
from clientfactory.core.response import Response

class SessionError(Exception):
    """Base exception for session-related errors."""
    pass

@dataclass
class SessionConfig:
    """Configuration for session behavior"""
    headers: dict = field(default_factory=dict)
    cookies: dict = field(default_factory=dict)
    auth: t.Optional[t.Tuple[str, str]] = None
    proxies: dict = field(default_factory=dict)
    verify: bool = True
    persist: bool = False
    maxretries: int = 3


class Session(AbstractContextManager):
    """
    Base session class that handles request execution and lifecycle management.

    The Session class is responsible for:
        - Maintaining persistent state across requests (cookies, auth)
        - Executing requests and returning responses
        - Applying authentication credentials
        - Handling request preparation and middleware

    Sessions can be used as context managers to ensure proper cleanup:
        ```python
        with Session() as session:
            response = session.send(request)
        ```
    """

    def __init__(self, config: t.Optional[SessionConfig] = None, auth: t.Optional["BaseAuth"] = None):
        """Initialize session with optional configuration and authentication."""
        log.debug("Initializing Session")
        log.info(f"DEBUGGING SESSION INIT - Received auth: {auth}")
        self.config = (config or SessionConfig())
        self.auth = auth
        log.info(f"DEBUGGING SESSION INIT - Set self.auth: {self.auth}")
        self._session = self._createsession()
        self._requesthooks = []
        self._responsehooks = []

    def _createsession(self) -> rq.Session:
        """Create and configure a requests session"""
        log.debug("Creating requests.Session")
        session = rq.Session()

        log.debug(f"Setting session headers: {self.config.headers}")
        session.headers.update(self.config.headers)

        log.debug(f"Setting session cookies: {self.config.cookies}")
        session.cookies.update(self.config.cookies)

        if self.config.auth:
            log.debug(f"Setting session auth: {self.config.auth}")
            session.auth = self.config.auth

        if self.config.proxies:
            log.debug(f"Setting session proxies: {self.config.proxies}")
            session.proxies.update(self.config.proxies)

        log.debug(f"Setting SSL verification: {self.config.verify}")
        session.verify = self.config.verify

        # configure retry behavior
        if self.config.maxretries > 0:
            log.debug(f"Configuring retry behavior: max_retries={self.config.maxretries}")
            adapter = rq.adapters.HTTPAdapter(max_retries=self.config.maxretries)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
        return session

    def addrequesthook(self, hook: t.Callable[[Request], Request]) -> None:
        """Add a request hook to modify requests before they are sent"""
        log.debug(f"Adding request hook: {hook}")
        self._requesthooks.append(hook)

    def addresponsehook(self, hook: t.Callable[[Response], Response]) -> None:
        """Add a response hook to modify responses after they are received"""
        log.debug(f"Adding response hook: {hook}")
        self._responsehooks.append(hook)

    def preparerequest(self, request: Request) -> rq.Request:
        """Prepare a Request for execution with requests libary"""
        log.info(f"DEBUGGING - Preparing request: {request}")
        log.info(f"DEBUGGING - Session headers before hooks: {self._session.headers}")
        log.info(f"DEBUGGING - Request headers before preparation: {request.headers}")

        log.debug(f"Preparing request: {request}")


        # apply session headers to request if not already set
        if self._session.headers:
            newheaders = dict(self._session.headers)
            if request.headers:
                newheaders.update(request.headers)
            request = request.clone(headers=newheaders)
            log.info(f"DEBUGGING - Applied session headers to request: {request.headers}")


        # apply request hooks
        for i, hook in enumerate(self._requesthooks):
            log.debug(f"DEBUGGING - Applying request hook {i+1}")
            log.debug(f"Applying request hook {i+1}/{len(self._requesthooks)}")
            request = hook(request)
            log.debug(f"Request after hook {i+1}: {request}")

        # apply authentication if available
        if self.auth:
            log.debug(f"DEBUGGING - Applying auth: {self.auth.__class__.__name__}")
            log.debug("Applying authentication to request")

            # ensure auth is authenticated
            if not self.auth.state.authenticated:
                log.info(f"Session: auth not authenticated, authenticating now")
                self.auth.authenticate()

            request = self.auth.prepare(request)
            log.debug(f"Request after auth: {request}")
            log.debug(f"DEBUGGING - Headers after auth: {request.headers}")
        else:
            log.debug(f"DEBUGGING - No auth available")

        prepared = request.prepare()
        log.debug(f"Request after preparation: {prepared}")

        # Check if URL has a scheme, log warning if not
        if not (prepared.url.startswith('http://') or prepared.url.startswith('https://')):
            log.warning(f"Request URL lacks scheme: {prepared.url}")

        # convert to requests.Request
        log.debug("Converting to requests.Request")
        req = rq.Request(
            method=prepared.method.value,
            url=prepared.url,
            params=prepared.params,
            headers=prepared.headers,
            cookies=prepared.cookies,
            json=prepared.json,
            data=prepared.data,
            files=prepared.files
        )
        return req


    def send(self, request: Request) -> Response:
        """Send a request and return a response"""
        log.info(f"DEBUGGING REQUEST SEND - Request: {request}")
        log.info(f"DEBUGGING REQUEST SEND - Self.auth: {self.auth}")

        try:
            log.debug("Preparing request for sending")
            log.info(f"DEBUGGING - Session object: {self._session}")
            log.info(f"DEBUGGING - Session headers: {self._session.headers}")
            log.info(f"DEBUGGING - Session auth: {self.auth}")
            req = self.preparerequest(request)
            prepared = self._session.prepare_request(req)
            log.debug(f"Final prepared request: {prepared.url} {prepared.method}")
            log.debug(f"Request headers: {prepared.headers}")

            log.debug("Sending request to server")
            resp = self._session.send(
                prepared,
                timeout=request.config.timeout,
                allow_redirects=request.config.allowredirects,
                stream=request.config.stream
            )
            log.debug(f"Received response: status={resp.status_code}")

            log.debug("Creating Response object")
            response = Response(
                statuscode=resp.status_code,
                rawcontent=resp.content,
                request=request,
                headers=dict(resp.headers)
            )

            # apply response hooks
            for i, hook in enumerate(self._responsehooks):
                log.debug(f"Applying response hook {i+1}/{len(self._responsehooks)}")
                response = hook(response)

            log.debug(f"Returning final response: {response}")
            return response
        except rq.RequestException as e:
            log.error(f"Request execution failed: {e}")
            raise SessionError(f"Request execution failed: {e}")

    def close(self) -> None:
        """Close the session and free resources"""
        log.debug("Closing session")
        self._session.close()

    def __enter__(self) -> Session:
        """Context manager entry point"""
        log.debug("Entering session context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point"""
        log.debug("Exiting session context")
        self.close()


class SessionBuilder:
    """Builder for creating Session instances with fluent configuration"""

    def __init__(self):
        """Initialize with default configuration"""
        log.debug("Creating SessionBuilder")
        self._config = SessionConfig()
        self._auth = None
        self._requesthooks = []
        self._responsehooks = []

    def headers(self, h: dict) -> SessionBuilder:
        """Set default headers"""
        log.debug(f"Setting headers: {h}")
        self._config.headers.update(h)
        return self

    def cookies(self, c: dict) -> SessionBuilder:
        """Set default cookies"""
        log.debug(f"Setting cookies: {c}")
        self._config.cookies.update(c)
        return self

    def auth(self, a: t.Any) -> SessionBuilder:
        """Set authentication handler"""
        log.debug(f"Setting auth: {a}")
        self._auth = a
        return self

    def proxies(self, p: dict) -> SessionBuilder:
        """Set proxy configuration"""
        log.debug(f"Setting proxies: {p}")
        self._config.proxies.update(p)
        return self

    def verify(self, v: bool) -> SessionBuilder:
        """Set SSL verification"""
        log.debug(f"Setting verify: {v}")
        self._config.verify = v
        return self

    def persist(self, p: bool = True) -> SessionBuilder:
        """Set session persistence"""
        log.debug(f"Setting persist: {p}")
        self._config.persist = p
        return self

    def maxretries(self, m: int) -> SessionBuilder:
        """Set maximum retries"""
        log.debug(f"Setting maxretries: {m}")
        self._config.maxretries = m
        return self

    def requesthook(self, hook: t.Callable[[Request], Request]) -> SessionBuilder:
        """Add a request hook"""
        log.debug(f"Adding request hook: {hook}")
        self._requesthooks.append(hook)
        return self

    def responsehook(self, hook: t.Callable[[Response], Response]) -> SessionBuilder:
        """Add a response hook"""
        log.debug(f"Adding response hook: {hook}")
        self._responsehooks.append(hook)
        return self

    def build(self) -> Session:
        """Build and return a Session with the configured options"""
        log.debug("Building Session")
        session = Session(config=self._config, auth=self._auth)
        for hook in self._requesthooks:
            session.addrequesthook(hook)
        for hook in self._responsehooks:
            session.addresponsehook(hook)
        return session
