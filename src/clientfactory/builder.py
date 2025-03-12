# ~/clientfactory/builder.py
from __future__ import annotations
import typing as t
from dataclasses import replace, asdict

from clientfactory.client import Client, ClientConfig
from clientfactory.auth.base import BaseAuth, NoAuth
from clientfactory.session.base import SessionConfig
from clientfactory.utils.request import RequestConfig
from loguru import logger as log

class ClientBuilder:
    """
    Fluent builder interface for configuring Client instances.

    Usage:
        client = ClientBuilder()\\
            .baseurl("https://api.example.com")\\
            .auth(ApiKeyAuth("mykey"))\\
            .build()
    """

    def __init__(self):
        self._config = ClientConfig()
        self._auth: BaseAuth = NoAuth()
        self._resources: list[t.Type] = []

    def baseurl(self, url: str) -> ClientBuilder:
        """Set the base URL for the client"""
        self._config = replace(self._config, baseurl=url)
        return self

    def auth(self, auth: BaseAuth) -> ClientBuilder:
        """Set the authentication handler"""
        self._auth = auth
        return self

    def sessioncfg(self, **kwargs) -> ClientBuilder:
        """Configure session behavior"""
        self._config = replace(
            self._config,
            session=SessionConfig(**kwargs)
        )
        return self

    def requestconfig(self, **kwargs) -> ClientBuilder:
        """Configure default request behavior"""
        # Start with existing request config values
        current = asdict(self._config.request)
        # Update with new values
        current.update(kwargs)
        # Create new config with all values
        self._config = replace(
            self._config,
            request=RequestConfig(**current)
        )
        return self

    def addresource(self, resource: t.Type) -> ClientBuilder:
        """Add a resource class to be registered with the client"""
        self._resources.append(resource)
        return self

    def headers(self, headers: dict) -> ClientBuilder:
        """Set default headers for all requests"""
        sessioncfg = replace(
            self._config.session,
            headers=headers
        )
        self._config = replace(
            self._config,
            session=sessioncfg
        )
        return self

    def cookies(self, cookies: dict) -> ClientBuilder:
        """Set default cookies for all requests"""
        sessioncfg = replace(
            self._config.session,
            cookies=cookies
        )
        self._config = replace(
            self._config,
            session=sessioncfg
        )
        return self

    def verifyssl(self, verify: bool = True) -> ClientBuilder:
        """Configure SSL verification"""
        sessioncfg = replace(
            self._config.session,
            verify=verify
        )
        self._config = replace(
            self._config,
            session=sessioncfg
        )
        return self

    def timeout(self, timeout: float) -> ClientBuilder:
        """Set default request timeout"""
        requestconfig = replace(
            self._config.request,
            timeout=timeout
        )
        self._config = replace(
            self._config,
            request=requestconfig
        )
        return self

    def build(self) -> Client:
        """Create and configure a new Client instance"""
        log.debug(f"builder.ClientBuilder.build | creating client with config: {self._config}")

        # Create client instance
        client = Client(
            baseurl=self._config.baseurl,
            auth=self._auth,
            config=self._config
        )

        # Register any resources
        for resource in self._resources:
            client.register(resource)

        return client
