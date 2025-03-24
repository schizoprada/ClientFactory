# ~/ClientFactory/src/clientfactory/resources/search.py
"""
Search Resource
---------------
Resource implementation specialized for search operations.
"""
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field
from loguru import logger as log

from clientfactory.core.resource import ResourceConfig, MethodConfig
from clientfactory.core.request import RM, RequestMethod, Request
from clientfactory.core.session import Session
from clientfactory.core.response import Response
from clientfactory.core.payload import Payload, Parameter, ParameterType
from clientfactory.resources.base import SpecializedResource

@dataclass
class SearchResourceConfig(ResourceConfig):
    """Configuration for search resources"""
    payload: t.Optional[Payload] = None
    requestmethod: RequestMethod = RM.GET
    # none of the specific param or defaults, these can all be managed by Payload
    # we dont want redundancy or excess

class SearchResource(SpecializedResource):
    """
    Resource implementation specialized for search operations.

    Provides enhanced functionality for search APIs including:
        - Paramter validation and mapping through Payload
        - Pagination handling through iterator methods
        - Result transformation and mapping
    """
    def __init__(self, session: Session, config: SearchResourceConfig):
        super().__init__(session, config)
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
        for k, v in self._attributes.items():
            if hasattr(config, k):
                setattr(config, k, v)


    def _setupspecialized(self):
        if (not hasattr(self, "search")) and ("search" not in self._config.methods):
            log.debug(f"Adding default search method")
            methodconfig = MethodConfig(
                name="search",
                method=self._searchconfig.requestmethod,
                path=self._searchconfig.path,
                payload=self._searchconfig.payload
            )
            self._config.methods["search"] = methodconfig
            setattr(self, "search", self._createmethod(methodconfig))
