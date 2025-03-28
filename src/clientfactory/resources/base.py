# ~/ClientFactory/src/clientfactory/resources/base.py
"""
Base Specialized Resource Class
-------------------------------
Provides foundation for specialized resource types with enhanced functionality
"""
from __future__ import annotations
import typing as t
from clientfactory.log import log

from clientfactory.core.resource import Resource, ResourceConfig
from clientfactory.core.session import Session
from clientfactory.core.payload import Payload

class SpecializedResource(Resource):
    """
    Base class for specialized resources with enhanced functionality.

    Extends the core Resource class with additional features needed by specialized resource types
    such as search and managed resources.
    """

    def __init__(self, session: Session, config: ResourceConfig, attributes: t.Optional[dict] = None):
        """Initialize specialized resource with session and configuration"""
        self._attributes = (attributes or {})
        self._processattributes(config)
        super().__init__(session, config)
        self._setupspecialized()

    def _setupspecialized(self):
        """Set up specialized resource functionality"""
        # hook for subclasses to implement
        pass

    def _processattributes(self, config: ResourceConfig):
        """
        Process class attributes and apply them to resource configuration.

        This method runs before the resource is fully initialized, allowing
        specialized resources to modify their configuration based on attributes.
        """
        pass

    def withconfig(self, **updates) -> SpecializedResource:
        """Create a new resource with updated configuration."""
        newcfg = ResourceConfig(
            name=self._config.name,
            path=self._config.path,
            methods=self._config.methods.copy(),
            children=self._config.children.copy(),
            parent=self._config.parent
        )
        for k, v in updates.items():
            if hasattr(newcfg, k):
                setattr(newcfg, k, v)

        return self.__class__(self._session, newcfg)
