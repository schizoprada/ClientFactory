# ~/ClientFactory/src/clientfactory/backends/base.py
from __future__ import annotations
import enum, typing as t
from dataclasses import dataclass, field

from clientfactory.core.request import Request, RequestMethod
from clientfactory.core.response import Response
from clientfactory.declarative import DeclarativeComponent

class BackendType(enum.Enum):
    """Types of backends for API communication"""
    REST = "rest"
    GRAPHQL = "graphql"
    ALGOLIA = "algolia"
    ELASTICSEARCH = "elasticsearch"
    CUSTOM = "custom"

class Backend(DeclarativeComponent):
    """
    Base backend definition.

    Backend (protocols) define how requests are formatted and responses are parsed
    for different API types.
    """
    __declarativetype__ = 'backend'
    type: BackendType = BackendType.REST
    method: RequestMethod = RequestMethod.GET
    responseprocessing: bool = False

    def __init__(self, type: BackendType, method: t.Optional[RequestMethod] = None, responseprocessing: bool = False):
        self.type = type
        if method:
            self.method = method


    def preparerequest(self, request: Request, data: dict) -> Request:
        """To be implemented by derivative classes"""
        return request

    def _responseprocessor(self, response: Response) -> t.Any:
        return response

    def processresponse(self, response: Response) -> t.Any:
        """To be implemented by derivative classes"""
        if self.responseprocessing:
            return self._responseprocessor(response)
        return response
