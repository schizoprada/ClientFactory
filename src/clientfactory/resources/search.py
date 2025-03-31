# ~/ClientFactory/src/clientfactory/resources/search.py
"""
Search Resource
---------------
Resource implementation specialized for search operations.
"""
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field
from clientfactory.log import log

from clientfactory.core.resource import ResourceConfig, MethodConfig
from clientfactory.core.request import RM, RequestMethod, Request
from clientfactory.core.session import Session
from clientfactory.core.response import Response
from clientfactory.core.payload import Payload, Parameter, ParameterType
from clientfactory.resources.base import SpecializedResource
from clientfactory.backends.base import Backend, BackendType


@dataclass
class SearchResourceConfig(ResourceConfig):
    """Configuration for search resources"""
    payload: t.Optional[Payload] = None
    requestmethod: RequestMethod = RM.GET
    backend: t.Optional[Backend] = None

class SearchResource(SpecializedResource):
    """
    Resource implementation specialized for search operations.

    Provides enhanced functionality for search APIs including:
        - Paramter validation and mapping through Payload
        - Pagination handling through iterator methods
        - Result transformation and mapping
    """
    __declarativetype__ = 'search'
    requestmethod: RequestMethod = RM.GET
    payload: t.Optional[Payload] = None
    oncall: bool = False
    backend: t.Optional[Backend] = None

    def __init__(self, session: Session, config: SearchResourceConfig, attributes: t.Optional[dict]=None, backend: t.Optional[Backend] = None, **kwargs):
        # Convert basic ResourceConfig to SearchResourceConfig if needed
        if not isinstance(config, SearchResourceConfig):
            requestmethod = None
            if attributes and 'requestmethod' in attributes:
                requestmethod = attributes['requestmethod']
                log.debug(f"Found requestmethod in attributes: {requestmethod}")
            elif hasattr(self, 'requestmethod'):
                requestmethod = self.requestmethod
                log.debug(f"Using instance requestmethod: {requestmethod}")
            searchconfig = SearchResourceConfig(
                name=config.name,
                path=config.path,
                methods=config.methods.copy(),
                children=config.children.copy(),
                parent=config.parent,
                payload=getattr(self, 'payload', None),
                requestmethod=(requestmethod or RM.GET)
            )
            config = searchconfig
        super().__init__(session, config, attributes, **kwargs)
        self._searchconfig = config


    def _processattributes(self, config: ResourceConfig):
        if not isinstance(config, SearchResourceConfig):
            searchconfig = SearchResourceConfig(
                name=config.name,
                path=config.path,
                methods=config.methods.copy(),
                children=config.children.copy(),
                parent=config.parent
            )
            config.__class__ = SearchResourceConfig
            for k, v in searchconfig.__dict__.items():
                setattr(config, k, v)
        if hasattr(self, 'backend') and self.backend:
            config.backend = self.backend


        from clientfactory.utils.internal import attributes
        if hasattr(self, '_attributes') and self._attributes:
            attributes.apply(
                config,
                self._attributes,
                overwrite=True,
                applytoconfig=True,
                applytometadata=False,
            )



    def _setupspecialized(self):
        if (not hasattr(self, "search")) and ("search" not in self._config.methods):
            log.debug(f"Adding default search method")

            from clientfactory.utils.internal import attributes
            sources = [self._config, self, self.__class__]

            payload = attributes.resolve('payload', sources)
            log.debug(f"Resolved payload: {payload}")

            method = attributes.resolve('requestmethod', sources, default=RM.GET)
            log.debug(f"Resolved requestmethod: {method}")

            methodconfig = MethodConfig(
                name="search",
                method=method,
                path=None,
                payload=payload
            )
            self._config.methods["search"] = methodconfig
            callablemethod = self._createmethod(methodconfig)
            setattr(self, "search", callablemethod)
            if self.oncall:
                self.__call__ = callablemethod
