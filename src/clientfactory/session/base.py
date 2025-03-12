# ~/clientfactory/session/base.py
from __future__ import annotations
import typing as t
import requests as rq
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import AbstractContextManager
from clientfactory.utils.request import Request, RequestError
from clientfactory.utils.response import Response
from clientfactory.auth.base import BaseAuth
from clientfactory.session.state import StateManager, FileStateStore, SessionState
from loguru import logger as log

class SessionError(Exception):
    """Base exception for session errors"""
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
    storepath: t.Optional[str] = None

class BaseSession(AbstractContextManager):
    """
    Base session class that handles request execution and lifecycle management.
    Provides hooks for authentication and request/response processing.
    """
    def __init__(self, config: t.Optional[SessionConfig]=None, auth: t.Optional[BaseAuth]=None):
        self.config = config or SessionConfig()
        self.auth = auth
        self._session = self.__session__()
        self._state = StateManager(
            FileStateStore(self.config.storepath)
            if (self.config.persist and self.config.storepath)
            else None
        )
    def __session__(self) -> rq.Session:
        """Create and configure requests session"""
        session = rq.Session()
        session.headers.update(self.config.headers) # set default headers
        session.cookies.update(self.config.cookies)
        if self.config.auth:
            session.auth = self.config.auth
        if self.config.proxies:
            session.proxies.update(self.config.proxies)
        session.verify = self.config.verify
        return session

    def __prep__(self, request: Request) -> rq.Request:
        request = request.prepare()

        log.debug(f"BaseSession.__prep__ | received request headers[{request.headers}]")
        log.debug(f"BaseSession.__prep__ | session config headers[{self.config.headers}]")
        # merge headers -- session defaults with request specifics
        headers = self.config.headers.copy()
        headers.update(request.headers)
        if self._state:
            self._state.update(lastrequest=datetime.now())
        return rq.Request(
            method=request.method.value,
            url=request.url,
            params=request.params,
            headers=headers,
            cookies=request.cookies,
            json=request.json,
            data=request.data,
            files=request.files
        )

    def execute(self, request:Request) -> Response:
        prepped = self.__prep__(request) # returns a requests.Request
        log.debug(f"BaseSession.execute | executing prepared request[{prepped.__dict__}]")
        lasterror = None
        for attempt in range(request.config.maxretries):
            try:
                preparedrequest = prepped.prepare() # prepares the requests.Request
                log.info(f"BaseSession.execute | sending prepared request: {preparedrequest}")
                resp = self._session.send(
                    preparedrequest,
                    timeout=request.config.timeout,
                    allow_redirects=request.config.allowredirects,
                    stream=request.config.stream
                )
                log.info(f"BaseSession.execute | response code: {resp.status_code}")
                response = Response(
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    raw_content=resp.content,
                    request=request
                )
                if self._state:
                    self._state.update(
                        failedattempts=0,
                        lastresponsecode=response.status_code
                    )
                return response
            except Exception as e:
                log.error(f"BaseSession.execute | attempt {attempt+1} failed | exception | {str(e)}")
                lasterror = e
                if self._state:
                    self._state.update(
                        failedattempts=(self._state.state.failedattempts+1)
                    )
                # could add backoff logic here
                continue
        raise SessionError(f"Failed after {request.config.maxretries} attempts: {lasterror}")

    def send(self, request: Request) -> Response:
        return self.execute(request)

    @property
    def state(self) -> t.Optional[SessionState]:
        """Access current session state"""
        return self._state.state if self._state else None

    def close(self):
        self._session.close()

    def __enter__(self) -> BaseSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (self._state and self.config.persist):
            self._state._save()
        self.close()
