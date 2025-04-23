# src/clientfactory/__init__.pyi

import typing as t

from clientfactory.core.request import RequestMethod
from clientfactory.core.payload import Payload
from clientfactory.auth.base import BaseAuth

T = t.TypeVar('T')
R = t.TypeVar('R', bound='Resource')

class Resource:
    """Base resource class"""
    pass

class SearchResource(Resource, t.Generic[T]):
    """Search resource type"""
    def search(self, **kwargs) -> T:...

class Client:
    """Base client class"""
    baseurl: str
    auth: t.Optional[BaseAuth]

    def __init__(self, baseurl: t.Optional[str] = None, auth: t.Optional[BaseAuth] = None) -> None: ...
    def register(self, resourcecls: type) -> None: ...
