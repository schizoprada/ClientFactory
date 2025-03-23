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
    auth: t.Optional[t.Tuple[str, str]] = None  # why tuple?
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
        self.config = (config or SessionConfig())
        self.auth = auth
        self._session = self._createsession()
        self._requesthooks = []
        self._responsehooks = []

    def _createsession(self) -> rq.Session:
        """Create and configure a requests session"""
        session = rq.Session()
        session.headers.update(self.config.headers)
        session.cookies.update(self.config.cookies)

        if self.config.auth:
            session.auth = self.config.auth

        if self.config.proxies:
            session.proxies.update(self.config.proxies)

        session.verify = self.config.verify

        # configure retry behavior
        if self.config.maxretries > 0:
            adapter = rq.adapters.HTTPAdapter(max_retries=self.config.maxretries) # Pyright: "adapters" is not a known attribute of module "requests"
            session.mount('http://', adapter)
            session.mount('https://', adapter)
        return session

    def addrequesthook(self, hook: t.Callable[[Request], Request]) -> None:
        """Add a request hook to modify requests before they are sent"""
        self._requesthooks.append(hook)

    def addresponsehook(self, hook: t.Callable[[Response], Response]) -> None:
        """Add a response hook to modify responses after they are received"""
        self._responsehooks.append(hook)

    def preparerequest(self, request: Request) -> rq.Request:
        """Prepare a Request for execution with requests libary"""
        # apply request hooks
        for hook in self._requesthooks:
            request = hook(request)

        # apply authentication if available
        if self.auth:
            request = self.auth.prepare(request)

        prepared = request.prepare()

        # convert to requests.Request
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
        try:
            req = self.preparerequest(request)
            prepared = self._session.prepare_request(req)

            resp = self._session.send(
                prepared,
                timeout=request.config.timeout,
                allow_redirects=request.config.allowredirects,
                stream=request.config.stream
            )

            response = Response(
                statuscode=resp.status_code,
                rawcontent=resp.content,
                request=request,
                headers=dict(resp.headers)
            )

            for hook in self._responsehooks:
                response = hook(response)

            return response
        except rq.RequestException as e:
            raise SessionError(f"Request execution failed: {e}")

    def close(self) -> None:
        """Close the session and free resources"""
        self._session.close()

    def __enter__(self) -> Session:
        """Context manager entry point"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point"""
        self.close()


class SessionBuilder:
    """Builder for creating Session instances with fluent configuration"""

    def __init__(self):
        """Initialize with default configuration"""
        self._config = SessionConfig()
        self._auth = None
        self._requesthooks = []
        self._responsehooks = []

    def headers(self, h: dict) -> SessionBuilder:
        """Set default headers"""
        self._config.headers.update(h)
        return self

    def cookies(self, c: dict) -> SessionBuilder:
        """Set default cookies"""
        self._config.cookies.update(c)
        return self

    def auth(self, a: t.Any) -> SessionBuilder:
        """Set authentication handler"""
        self._auth = a
        return self

    def proxies(self, p: dict) -> SessionBuilder:
        """Set proxy configuration"""
        self._config.proxies.update(p)
        return self

    def verify(self, v: bool) -> SessionBuilder:
        """Set SSL verification"""
        self._config.verify = v
        return self

    def persist(self, p: bool = True) -> SessionBuilder:
        """Set session persistence"""
        self._config.persist = p
        return self

    def maxretries(self, m: int) -> SessionBuilder:
        """Set maximum retries"""
        self._config.maxretries = m
        return self

    def requesthook(self, hook: t.Callable[[Request], Request]) -> SessionBuilder:
        """Add a request hook"""
        self._requesthooks.append(hook)
        return self

    def responsehook(self, hook: t.Callable[[Response], Response]) -> SessionBuilder:
        """Add a response hook"""
        self._responsehooks.append(hook)
        return self

    def build(self) -> Session:
        """Build and return a Session with the configured options"""
        session = Session(config=self._config, auth=self._auth)
        for hook in self._requesthooks:
            session.addrequesthook(hook)
        for hook in self._responsehooks:
            session.addresponsehook(hook)
        return session
