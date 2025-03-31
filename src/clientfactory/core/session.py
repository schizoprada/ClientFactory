# ~/ClientFactory/src/clientfactory/core/session.py
"""
Session Class
-------------
Defines the core Session class for executing HTTP requests.
The Session handles authentication, request execution, and maintains state.
"""
from __future__ import annotations
import typing as t, requests as rq, traceback as tb
from dataclasses import dataclass, field
from contextlib import AbstractContextManager
import urllib.parse
from clientfactory.log import log

from clientfactory.core.request import Request, RequestConfig
from clientfactory.core.response import Response
from clientfactory.declarative import DeclarativeComponent


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


class Session(DeclarativeComponent):
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
    __declarativetype__ = 'session'
    config: t.Optional[SessionConfig] = None
    auth: t.Optional["BaseAuth"] = None
    headers: t.Optional[dict] = None
    cookies: t.Optional[dict] = None
    initialrequest: t.Optional[Request] = None

    def __init__(
            self,
            config: t.Optional[SessionConfig] = None,
            auth: t.Optional["BaseAuth"] = None,
            headers: t.Optional[dict] = None,
            cookies: t.Optional[dict] = None,
            initialrequest: t.Optional[Request] = None,
            **kwargs
        ):
        """Initialize session with optional configuration and authentication."""
        log.debug("Initializing Session")
        super().__init__(**kwargs)

        from clientfactory.utils.internal import attributes
        sources = [self, self.__class__]

        if auth is None:
            auth = attributes.resolve('auth', sources)
        if headers is None:
            headers = attributes.resolve('headers', sources)
        if cookies is None:
            cookies = attributes.resolve('cookies', sources)
        if initialrequest is None:
            log.info(f"Session.__init__ | resolving initialrequest")
            initialrequest = attributes.resolve('initialrequest', sources)
            log.info(f"Session.__init__ | initialrequest after attribute resolution: {initialrequest}")
        config  = (config or SessionConfig())
        self.auth = auth
        self.headers = ({} if headers is None else headers)
        self.cookies = ({} if cookies is None else cookies)

        if self.headers:
            if isinstance(self.headers, dict):
                config.headers.update(self.headers)
            elif hasattr(self.headers, 'static'):
                config.headers.update(self.headers.static)

        if self.cookies:
            if isinstance(self.cookies, dict):
                config.cookies.update(self.cookies)

        self.config = config
        self._session = self._createsession()
        self._requesthooks = []
        self._responsehooks = []
        self.initialrequest = initialrequest

        if initialrequest:
            log.info(f"Session.__init__ | calling self._requestinitial")
            self._requestinitial(initialrequest)

    @classmethod
    def _processclassattributes(cls) -> None:
        super()._processclassattributes()
        for name in ('headers', 'cookies', 'auth'):
            if hasattr(cls, name) and (not cls.hasmetadata(name)):
                cls.setmetadata(name, getattr(cls, name))


    def _requestinitial(self, request: Request) -> None:
        """
        Process an initial request to set up session headers and cookies.
        """
        try:
            from requests.utils import dict_from_cookiejar
            log.info(f"Setting up session with initial request: {request}")
            req = request.clone()
            response = self.send(req)

            if not response.ok:
                log.info(f"Initial request failed with status: {response.statuscode}")
                return

            # Update session headers with response headers
            headerupdates = request.headers.copy()
            for key, value in response.headers.items():
                headerupdates[key] = value

            if headerupdates:
                self._session.headers.update(headerupdates)
                log.info(f"Updated session headers: {headerupdates}")

            # Update session cookies with response cookies
            if response.cookies:
                self._session.cookies.update(response.cookies)
                log.info(f"Updated session cookies: {response.cookies}")

            self.headers = dict(self._session.headers)
            self.cookies = dict_from_cookiejar(self._session.cookies)
            log.info(f"Session initialization complete")
            log.info(f"Final session headers: {self.headers}")
            log.info(f"Final session cookies: {self.cookies}")
        except Exception as e:
            log.info(f"Error processing initial request: {e}", tb.format_exc())

    def _createsession(self) -> rq.Session:
        """Create and configure a requests session"""
        log.debug("Creating requests.Session")
        session = rq.Session()

        applyheaders = {}
        applycookies = {}

        # 1. start with config headers
        if hasattr(self, 'config') and self.config:
            applyheaders.update(self.config.headers)

        # 2. add headers from instance attributes (set via contructor)
        if hasattr(self, '_headers') and self.headers:
            if isinstance(self.headers, dict):
                applyheaders.update(self.headers)
            elif hasattr(self.headers, 'static'):
                applyheaders.update(self.headers.static)

        # 3. add headers from class metadata (declarative attributes)
        if hasattr(self.__class__, '__metadata__') and ('headers' in self.__class__.__metadata__):
            metadataheaders = self.__class__.__metadata__['headers']
            if isinstance(metadataheaders, dict):
                applyheaders.update(metadataheaders)
            elif hasattr(metadataheaders, 'static'):
                applyheaders.update(metadataheaders.static)

        # apply all collected headers
        log.debug(f"Session._createsession | applying headers: {applyheaders}")
        session.headers.update(applyheaders)

        # 1. start with config cookies
        if hasattr(self, 'config') and self.config:
            applycookies.update(self.config.cookies)

        # 2. add cookies from instance attributes (set via contructor)
        if hasattr(self, '_cookies') and self.cookies:
            if isinstance(self.cookies, dict):
                applycookies.update(self.cookies)


        # 3. add cookies from class metadata (declarative attributes)
        if hasattr(self.__class__, '__metadata__') and ('cookies' in self.__class__.__metadata__):
            metadatacookies = self.__class__.__metadata__['cookies']
            if isinstance(metadatacookies, dict):
                applycookies.update(metadatacookies)

        log.debug(f"Session._createsession | applying cookies: {applycookies}")
        session.cookies.update(applycookies)

        if self.config.auth:
            log.debug(f"Session._createsession | setting auth: {self.config.auth}")
            session.auth = self.config.auth

        if self.config.proxies:
            log.debug(f"Session._createsession | setting proxies: {self.config.proxies}")
            session.proxies = self.config.proxies

        session.verify = self.config.verify

        if self.config.maxretries > 0:
            adapter = rq.adapters.HTTPAdapter(max_retries=self.config.maxretries)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

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

        if self._session.cookies:
            newcookies = {k:v for k, v in self._session.cookies.items()}
            if request.cookies:
                newcookies.update(request.cookies)
            request = request.clone(cookies=newcookies)

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
        try:
            from requests.utils import dict_from_cookiejar
            log.debug("Preparing request for sending")

            if self._session.headers:
                newheaders = dict(self._session.headers)
                if request.headers:
                    newheaders.update(request.headers)
                request = request.clone(headers=newheaders)

            if self._session.cookies:
                newcookies = {k:v for k,v in self._session.cookies.items()}
                if request.cookies:
                    newcookies.update(request.cookies)
                request = request.clone(cookies=newcookies)


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
                headers=dict(resp.headers),
                cookies=dict_from_cookiejar(resp.cookies)
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
