# ~/ClientFactory/src/clientfactory/clients/search/base.py
from __future__ import annotations
import enum, typing as t
from dataclasses import dataclass, field
from clientfactory.client import Client
from clientfactory.utils import Request, Response, RequestMethod
from clientfactory.resources import Resource, ResourceConfig, get, post, put, delete, preprocess, postprocess
from clientfactory.clients.search.core import Parameter, ParameterType, Payload, Protocol, ProtocolType, SearchResourceConfig
from clientfactory.clients.search.adapters import Adapter
from loguru import logger as log




class Search:
    """Base search functionality shared between clients and resources"""
    protocol: Protocol
    payload: t.Optional[Payload] = None
    adapter: t.Optional[Adapter] = None
    oncall: bool = False

    def __init__(self):
        log.debug(f"Search.__init__ | initializing search[{self.__class__.__name__}]")
        if not hasattr(self, 'protocol'):
            log.error(f"Search.__init__ | missing required protocol")
            raise ValueError("Search requires protocol")
        if not isinstance(self.protocol, Protocol):
            raise ValueError(f"Invalid protocol type: {type(self.protocol)}")

        if (not hasattr(self, 'payload')) or (self.payload is None):
            log.debug(f"Search.__init__ | initializing default payload")
            self.payload = Payload()

        if (not hasattr(self, 'adapter')) or (self.adapter is None):
            log.debug(f"Search.__init__ | initializing adapter")
            self._adapt()

        if self.oncall:
            log.debug(f"Search.__init__ | enabling oncall functionality")
            ogcall = self.__call__
            def caller(*args, **kwargs):
                params = kwargs
                if hasattr(self, 'payload'):
                    if not self.payload.validate(**kwargs):
                        return None
                    params = self.payload.map(**kwargs)
                return ogcall(*args, **kwargs)
            self.__call__ = caller


    def _adapt(self):
        log.debug(f"Search._adapt | selecting adapter for protocol[{self.protocol.type}]")
        config = getattr(self, 'adaptercfg', None)
        match self.protocol.type:
            case ProtocolType.REST:
                from clientfactory.clients.search.adapters import REST
                self.adapter = REST(config=config) if config else REST()
                log.debug(f"Search._adapt | initialized REST adapter")
            case ProtocolType.ALGOLIA:
                from clientfactory.clients.search.adapters import Algolia
                self.adapter = Algolia(config=config) if config else Algolia()
                log.debug(f"Search._adapt | initialized Algolia adapter")
            case ProtocolType.GRAPHQL:
                from clientfactory.clients.search.adapters import GraphQL
                self.adapter = GraphQL(config=config) if config else GraphQL()
                log.debug(f"Search._adapt | initialized GraphQL adapter")
            case _:
                log.error(f"Search._adapt | unsupported protocol type[{self.protocol.type}]")
                raise ValueError(f"Unsupported protocol type: {self.protocol.type}")

    def _execute(self, transformed:bool=False, **kwargs):
        """Execute search based on protocol type"""
        log.debug(f"Search._execute | executing search with kwargs[{kwargs}]")
        if transformed:
            log.info(f"Search._execute | using kwargs directly, theyve already been transformed")
            params = kwargs
            options = None
        else:
            params = {k:v for k, v in kwargs.items() if k in self.payload.parameters}
            options = {k:v for k, v in kwargs.items() if (k not in self.payload.parameters) or (k in self.payload.parameters and k in kwargs)}
            if not self.payload.validate(**params):
                raise ValueError(f"Invalid parameters: {params}")

            params = self.adapter.formatall(**(self.payload.map(**params)))
        log.debug(f"Search._execute | formatted parameters[{params}]")

        url = self.baseurl
        if hasattr(self, 'path'):
            url = f"{self.baseurl.rstrip('/')}/{self.path.lstrip('/')}"
        log.info(f"Search._execute | using URL[{url}]")

        match self.protocol.type:
            case ProtocolType.REST:
                if self.protocol.method == RequestMethod.GET:
                    log.debug(f"Search._execute | building GET request")
                    request = Request(
                        method=self.protocol.method,
                        url=url,
                        params=(options if options else params),
                        kwargs=kwargs,
                        headers=kwargs.get('headers', self._session.config.headers),
                        cookies=kwargs.get('cookies', self._session.config.cookies)
                    )
                else:
                    log.debug(f"Search._execute | building {self.protocol.method} request")
                    request = Request(
                        method=self.protocol.method,
                        url=url,
                        **{self.payload.key: params},
                        kwargs=kwargs,
                        headers=kwargs.get('headers', self._session.config.headers),
                        cookies=kwargs.get('cookies', self._session.config.cookies)
                    )
                log.debug(f"Search._execute | sending request[{request}]")
                if self._session.auth:
                    log.debug(f"Search._execute | session auth detected | applying to request")
                    request = self._session.auth.prepare(request)
                return self._session.send(request)

            case ProtocolType.ALGOLIA:
                request = Request(
                    method=RequestMethod.POST,
                    url=url,
                    **{self.payload.key: params},
                    kwargs=kwargs,
                    headers=kwargs.get('headers', self._session.config.headers),
                    cookies=kwargs.get('cookies', self._session.config.cookies)
                )
                if self._session.auth:
                    log.debug(f"Search._execute | session auth detected | applying to request")
                    request = self._session.auth.prepare(request)
                return self._session.send(request)

            case ProtocolType.GRAPHQL:
                log.debug(f"Search._execute | building GraphQL request")
                request = Request(
                    method = RequestMethod.POST,
                    url=url,
                    json=params, # GQL expects JSON key payload
                    kwargs=kwargs,
                    headers=kwargs.get('headers', self._session.config.headers),
                    cookies=kwargs.get('cookies', self._session.config.cookies)
                )
                log.debug(f"Search._execute | sending GraphQL request[{request}]")
                if self._session.auth:
                    log.debug(f"Search._execute | session auth detected | applying to request")
                    request = self._session.auth.prepare(request)
                return self._session.send(request)

            case _:
                raise ValueError(f"Unsupported protocol type: {self.protocol.type}")

    def __call__(self, **kwargs):
        """Default search implementation when oncall=True"""
        if not self.oncall:
            raise NotImplementedError("__call__ is only available when oncall=True")
        if hasattr(self, 'execute'):
            log.debug(f"Search.__call__ | using `execute` method")
            return self.execute(**kwargs)
        log.debug(f"Search.__call__ | using `_execute` method")
        return self._execute(**kwargs)

class SearchClient(Search, Client):
    """Client-level search implementation"""
    def __init__(self):
        Search.__init__(self)
        Client.__init__(self)

class SearchResource(Search, Resource):
    """Resource-level search implementation"""
    def __init__(self, *args, **kwargs):
        Resource.__init__(self, *args, **kwargs)
        if not isinstance(self._config, SearchResourceConfig):
            self._config = SearchResourceConfig.FromResourceConfig(
                self._config,
                protocol=getattr(self._resourcecls, 'protocol', None),
                payload=getattr(self._resourcecls, 'payload', None),
                oncall=getattr(self._resourcecls, 'oncall', False),
                adaptercfg=getattr(self._resourcecls, 'adaptercfg', None)
            )
        self.protocol = self._config.protocol
        self.payload = self._config.payload
        self.oncall = self._config.oncall
        self.adaptercfg = self._config.adaptercfg
        self.baseurl = self._config.parent.baseurl if self._config.parent else None
        self.path = self._config.path
        Search.__init__(self)

    def execute(self, **kwargs):
        """Alias for _execute to match resource method naming"""
        log.debug(f"SearchResource.execute | starting execute with kwargs: {kwargs}")
        if not self.payload.validate(**kwargs):
            raise ValueError(f"Invalid Parameters: {kwargs}")

        params = self.payload.map(**kwargs)
        log.debug(f"SearchResource.execute | after payload mapping: {params}")
        transformed = False

        if hasattr(self._config, 'pipeline'):
            if hasattr(self._config.pipeline, 'transforms'):
                log.debug(f"SearchResource.execute | pipeline exists, transforms: {[t.__class__.__name__ for t in self._config.pipeline.transforms]}")
                params = self._config.pipeline(params)
                transformed = True
                log.debug(f"SearchResource.execute | after transform pipeline: {params}")

        log.debug(f"SearchResource.execute | calling _execute with params: {params}")
        return super()._execute(transformed=transformed, **params)
