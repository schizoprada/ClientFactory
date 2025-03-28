# ~/ClientFactory/src/clientfactory/client/builder.py
"""
Client Builder
--------------
This module defines the ClientBuilder class which provides a fluent API for constructing and configuring Client instances.
"""
from __future__ import annotations
import typing as t, functools as fn
from clientfactory.log import log

from clientfactory.auth import BaseAuth
from clientfactory.client.base import Client
from clientfactory.client.config import ClientConfig


def buildermethod(func):
    @fn.wraps(func)
    def wrapper(self, *args, **kwargs):
        log.debug(f"ClientBuilder: calling {func.__name__} with args={args}, kwargs={kwargs}")
        func(self, *args, **kwargs)
        return self
    return wrapper


class ClientBuilder:
    """Fluent builder interface for configuring Client instances."""

    def __init__(self):
        """Initialize a new builder instance"""
        log.debug("Creating ClientBuilder")
        self._config = ClientConfig()
        self._auth = None
        self._resources = []

    @buildermethod
    def baseurl(self, url: str) -> ClientBuilder:
        """Set the base URL for the client"""
        log.debug(f"Setting baseurl: {url}")
        self._config.baseurl = url

    @buildermethod
    def auth(self, auth: BaseAuth) -> ClientBuilder:
        """Set the authentication handler"""
        log.debug(f"Setting auth: {auth}")
        self._auth = auth

    @buildermethod
    def headers(self, h: dict[str, str]) -> ClientBuilder:
        """Set default headers for all requests"""
        log.debug(f"Setting headers: {h}")
        self._config.headers.update(h)

    @buildermethod
    def cookies(self, c: dict[str, str]) -> ClientBuilder:
        """Set default cookies for all requets"""
        log.debug(f"Setting cookies: {c}")
        self._config.cookies.update(c)

    @buildermethod
    def verifyssl(self, verify: bool = True) -> ClientBuilder:
        """Configure SSL verification"""
        log.debug(f"Setting verifyssl: {verify}")
        self._config.verifyssl = verify

    @buildermethod
    def timeout(self, count: float) -> ClientBuilder:
        """Set request timeout"""
        log.debug(f"Setting timeout: {count}")
        self._config.timeout = count

    @buildermethod
    def followredirects(self, follow: bool = True) -> ClientBuilder:
        """Configure HTTP redirect following"""
        log.debug(f"Setting followredirects: {follow}")
        self._config.followredirects = follow

    @buildermethod
    def register(self, resource: t.Type) -> ClientBuilder:
        """Register a resource class"""
        log.debug(f"Registering resource: {resource.__name__}")
        self._resources.append(resource)

    def build(self) -> Client:
        """Build and return a configured Client instance"""
        log.debug(f"Building client with baseurl: {self._config.baseurl}")
        client = Client(
            baseurl=self._config.baseurl,
            auth=self._auth,
            config=self._config
        )
        log.debug(f"Client built, registering {len(self._resources)} resources")
        for resourcecls in self._resources:
            log.debug(f"Registering resource: {resourcecls.__name__}")
            client.register(resourcecls)
        log.debug("Client build complete")
        return client
