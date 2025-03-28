# ~/ClientFactory/src/clientfactory/utils/internal/attribution.py
"""
Attribute Resolution Utilities
-----------------------------
Provides utilities for discovering and resolving attributes from various sources.
"""
from __future__ import annotations
import typing as t
from clientfactory.log import log


class attributes:
    @staticmethod
    def resolve(name: str, sources: list[t.Any], default: t.Any = None, attrnames: t.Optional[list[str]] = None,
                silent: bool = False, checkorder: t.Iterable = ('instance', 'config', 'metadata', 'dict')):
        """
        Resolve an attribute from multiple sources in priority order.

        Args:
            name: Name of the attribute to resolve
            sources: List of objects to check for the attribute, in priority order
            default: Default value to return if attribute not found
            attrnames: Optional list of alternative attribute names to check
            silent: If True, suppress log messages
            checkorder: Order to check attribute locations (tuple to ensure ordering)

        Returns:
            The resolved attribute value or default
        """
        checkfor = [name]
        if attrnames:
            checkfor.extend(attrnames)

        # Check each source for each attribute name
        for source in sources:
            if source is None:
                continue

            for attrname in checkfor:
                for location in checkorder:
                    if (location == 'config') and (hasattr(source, '_config')):
                        if hasattr(source._config, attrname):
                            value = getattr(source._config, attrname)
                            if not silent:
                                log.debug(f"Found ({attrname}={value}) on {source.__class__.__name__}._config")
                            return value

                    elif location == 'instance':
                        if hasattr(source, attrname):
                            value = getattr(source, attrname)
                            if not silent:
                                log.debug(f"Found ({attrname}={value}) on {source.__class__.__name__}")
                            return value

                    elif location == 'metadata':
                        if hasattr(source, '__metadata__') and (attrname in source.__metadata__):
                            value = source.__metadata__[attrname]
                            if not silent:
                                log.debug(f"Found ({attrname}={value}) in {source.__class__.__name__}.__metadata__")
                            return value

                    elif location == 'dict':
                        if hasattr(source, '__getitem__'):
                            try:
                                value = source[attrname]
                                if not silent:
                                    log.debug(f"Found ({attrname}={value}) via item access on {source.__class__.__name__}")
                                return value
                            except (KeyError, TypeError, IndexError):
                                pass

        # Only return default after checking all sources
        if not silent:
            log.debug(f"Attribute {name} not found in any source, using default: {default}")
        return default

    @staticmethod
    def collect(
        source: t.Any,
        attrnames: list[str],
        includemetadata: bool = True,
        includeconfig: bool = True,
        includeparent: bool = False,
        includeprivate: bool = False,
        silent: bool = False
    ) -> dict[str, t.Any]:
        """
        Collect attributes from a source into a dictionary.

        Args:
            source: Source object to collect attributes from
            attrnames: List of attribute names to collect
            includemetadata: If True, also check metadata for attributes
            includeconfig: If True, also check _config for attributes
            includeparent: If True, also check parent classes
            includeprivate: If True, include private attributes (starting with _)
            silent: If True, suppress log messages

        Returns:
            Dictionary of collected attributes
        """
        result = {}

        # Filter attribute names based on privacy setting
        if not includeprivate:
            attrnames = [name for name in attrnames if not name.startswith('_')]

        # Direct attributes
        for name in attrnames:
            if hasattr(source, name):
                result[name] = getattr(source, name)
                if not silent:
                    log.debug(f"Collected {name}={result[name]} from {source.__class__.__name__}")

        # Config attributes
        if includeconfig and hasattr(source, '_config'):
            for name in attrnames:
                if name not in result and hasattr(source._config, name):
                    result[name] = getattr(source._config, name)
                    if not silent:
                        log.debug(f"Collected {name}={result[name]} from {source.__class__.__name__}._config")

        # Metadata attributes
        if includemetadata and hasattr(source, '__metadata__'):
            for name in attrnames:
                if name not in result and name in source.__metadata__:
                    result[name] = source.__metadata__[name]
                    if not silent:
                        log.debug(f"Collected {name}={result[name]} from {source.__class__.__name__}.__metadata__")

        # Parent class attributes
        if includeparent and hasattr(source, '__class__'):
            for base in source.__class__.__bases__:
                for name in attrnames:
                    if name not in result and hasattr(base, name):
                        result[name] = getattr(base, name)
                        if not silent:
                            log.debug(f"Collected {name}={result[name]} from parent class {base.__name__}")

        return result

    @staticmethod
    def apply(
        target: t.Any,
        attributes: dict[str, t.Any],
        overwrite: bool = True,
        applytoconfig: bool = True,
        applytometadata: bool = True,
        silent: bool = False
    ) -> t.Any:
        """
        Apply attributes to a target object.

        Args:
            target: Target object to apply attributes to
            attributes: Dictionary of attributes to apply
            overwrite: If True, overwrite existing attributes
            applytoconfig: If True, also apply to _config if it exists
            applytometadata: If True, also add to metadata
            silent: If True, suppress log messages

        Returns:
            The modified target object
        """
        for name, value in attributes.items():
            # Skip if attribute exists and overwrite is False
            if hasattr(target, name) and not overwrite:
                continue

            # Apply to object attribute
            setattr(target, name, value)
            if not silent:
                log.debug(f"Applied {name}={value} to {target.__class__.__name__}")

            # Also apply to config if available
            if applytoconfig and hasattr(target, '_config') and hasattr(target._config, name):
                setattr(target._config, name, value)
                if not silent:
                    log.debug(f"Applied {name}={value} to {target.__class__.__name__}._config")

            # Also apply to metadata if available
            if applytometadata and hasattr(target, '__metadata__'):
                target.__metadata__[name] = value
                if not silent:
                    log.debug(f"Applied {name}={value} to {target.__class__.__name__}.__metadata__")

        return target


class Attributer:
    """
    Class-based interface for attribute resolution and manipulation.
    Allows for more stateful interaction with attributes.
    """

    def __init__(self, sources: t.Optional[list[t.Any]] = None, silent: bool = False):
        """
        Initialize the attributer with default sources.

        Args:
            sources: Default sources to check for attributes
            silent: If True, suppress log messages
        """
        self.sources = sources or []
        self.silent = silent
        self.resolutionorder = ['config', 'direct', 'metadata', 'dict']
        self.collected = {}

    def addsource(self, source: t.Any) -> 'Attributer':
        """
        Add a source to the attributer.

        Args:
            source: Source object to add

        Returns:
            Self for chaining
        """
        if source is not None:
            self.sources.append(source)
        return self

    def setresolutionorder(self, order: list[str]) -> 'Attributer':
        """
        Set the resolution order.

        Args:
            order: New resolution order

        Returns:
            Self for chaining
        """
        self.resolutionorder = order
        return self

    def resolve(self, name: str, default: t.Any = None, attrnames: t.Optional[list[str]] = None) -> t.Any:
        """
        Resolve an attribute from the sources.

        Args:
            name: Name of the attribute to resolve
            default: Default value to return if attribute not found
            attrnames: Optional list of alternative attribute names to check

        Returns:
            The resolved attribute value or default
        """
        return attributes.resolve(
            name,
            self.sources,
            default,
            attrnames,
            self.silent,
            self.resolutionorder
        )

    def collect(self, attrnames: list[str], **kwargs) -> 'Attributer':
        """
        Collect attributes from the sources.

        Args:
            attrnames: List of attribute names to collect
            **kwargs: Additional options for collection

        Returns:
            Self for chaining
        """
        for source in self.sources:
            collected = attributes.collect(
                source,
                attrnames,
                silent=self.silent,
                **kwargs
            )
            self.collected.update(collected)
        return self

    def apply(self, target: t.Any, **kwargs) -> t.Any:
        """
        Apply collected attributes to a target.

        Args:
            target: Target object to apply attributes to
            **kwargs: Additional options for application

        Returns:
            The modified target object
        """
        return attributes.apply(
            target,
            self.collected,
            silent=self.silent,
            **kwargs
        )

    def get(self, name: str, default: t.Any = None) -> t.Any:
        """
        Get a collected attribute.

        Args:
            name: Name of the attribute to get
            default: Default value to return if not found

        Returns:
            The attribute value or default
        """
        return self.collected.get(name, default)

    def getall(self) -> dict[str, t.Any]:
        """
        Get all collected attributes.

        Returns:
            Dictionary of collected attributes
        """
        return self.collected.copy()
