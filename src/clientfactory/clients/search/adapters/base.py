# ~/ClientFactory/src/clientfactory/clients/search/adapters/base.py
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields

@dataclass
class Adapter(ABC):

    @abstractmethod
    def formatparams(self, params, **kwargs): pass

    @abstractmethod
    def formatfilters(self, filters, **kwargs): pass

    @abstractmethod
    def formatpagination(self, page, hits, **kwargs): pass

    @abstractmethod
    def formatsorting(self, field, order, **kwargs): pass

    def formatall(self, **kwargs) -> dict:
        """Format all parameters into final request format"""
        formatted = {}

        # Basic params
        if 'params' in kwargs:
            formatted.update(self.formatparams(kwargs['params']))

        # Filters
        if 'filters' in kwargs:
            formatted.update(self.formatfilters(kwargs['filters']))

        # Pagination
        if any(k in kwargs for k in ['page', 'hits']):
            formatted.update(self.formatpagination(
                kwargs.get('page', 1),
                kwargs.get('hits', 20)
            ))

        # Sorting
        if any(k in kwargs for k in ['sort', 'order']):
            formatted.update(self.formatsorting(
                kwargs.get('sort'),
                kwargs.get('order', 'asc')
            ))

        return formatted
