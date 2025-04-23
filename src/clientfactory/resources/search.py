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


T = t.TypeVar('T')

@dataclass
class SearchResourceConfig(ResourceConfig):
    """Configuration for search resources"""
    payload: t.Optional[Payload] = None
    requestmethod: RequestMethod = RM.GET
    backend: t.Optional[Backend] = None

class SearchResource(SpecializedResource, t.Generic[T]):
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


    def _gendocs(self, payload):
        """Dynamically generate docstring for search method based on payload parameters"""
        if not payload:
            return "Search method with no specified parameters"
        lines = ["Search Params: "]
        lines.append("-------------")

        if hasattr(payload, 'parameters'):
            for name, param in payload.parameters.items():
                paramtype = param.type.value if hasattr(param, 'type') else "Any"
                default = f" (default: {param.default})" if hasattr(param, 'default') and param.default is not None else ""
                required = " [required]" if hasattr(param, 'required') and param.required else ""
                description = param.description if hasattr(param, 'description') and param.description else ""
                lines.append(f"{name} : {paramtype}{required}{default}")
                if description:
                    lines.append(f"    {description}")

        # Handle nested payload
        if hasattr(payload, 'root') and hasattr(payload, 'static'):
            lines.append("")
            lines.append("This search uses a nested payload structure.")
            lines.append(f"Root field: {payload.root}")

            if payload.static:
                lines.append("")
                lines.append("Static parameters (automatically included):")
                for key, value in payload.static.items():
                    lines.append(f"    {key}: {value}")

        # Add return value documentation
        lines.append("")
        lines.append("Returns:")
        lines.append("--------")
        lines.append("Response")
        lines.append("    The API response containing search results.")

        return "\n".join(lines)

    def _setupspecialized(self):
        if (not hasattr(self, "search")) and ("search" not in self._config.methods):
            log.debug(f"Adding default search method")

            from clientfactory.utils.internal import attributes
            sources = [self._config, self, self.__class__]

            payload = attributes.resolve('payload', sources)
            log.debug(f"Resolved payload: {payload}")
            setattr(self, "payload", payload)


            method = attributes.resolve('requestmethod', sources, default=RM.GET)
            log.debug(f"Resolved requestmethod: {method}")

            docstring = self._gendocs(payload)


            methodconfig = MethodConfig(
                name="search",
                method=method,
                path=None,
                payload=payload,
                description=docstring
            )
            self._config.methods["search"] = methodconfig
            callablemethod = self._createmethod(methodconfig)
            callablemethod.__doc__ = docstring

            setattr(self, "search", callablemethod)
            if self.oncall:
                self.__call__ = callablemethod
