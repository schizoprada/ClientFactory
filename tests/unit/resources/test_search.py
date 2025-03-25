# ~/ClientFactory/tests/unit/resources/test_search.py
from __future__ import annotations
import pytest

from clientfactory.core.request import RequestMethod as RM
from clientfactory.core.payload import Payload, Parameter
from clientfactory.core.session import Session
from clientfactory.resources.search import SearchResource, SearchResourceConfig
from clientfactory.decorators import searchresource

def test_search_resource_metadata():
    """Test that search resource attributes are properly processed into metadata"""
    class CustomSearch(SearchResource):
        requestmethod = RM.POST
        payload = Payload(
            query=Parameter(required=True),
            limit=Parameter(default=20)
        )

    assert CustomSearch.getmetadata('requestmethod') == RM.POST
    assert isinstance(CustomSearch.getmetadata('payload'), Payload)

def test_search_resource_decorator():
    """Test the @searchresource decorator"""
    @searchresource(path="search")
    class Search:
        requestmethod = RM.POST
        payload = Payload(
            query=Parameter(required=True)
        )

    assert issubclass(Search, SearchResource)
    assert Search.getmetadata('path') == "search"
    assert Search.getmetadata('requestmethod') == RM.POST

def test_search_method_setup():
    """Test that the search method is properly configured"""
    class CustomSearch(SearchResource):
        requestmethod = RM.POST
        payload = Payload(
            query=Parameter(required=True)
        )

    session = Session()
    config = SearchResourceConfig(
        name="search",
        path="search"
    )

    resource = CustomSearch(session, config)
    assert hasattr(resource, "search")
    assert "search" in resource._config.methods

    method_config = resource._config.methods["search"]
    assert method_config.method == RM.POST
    assert method_config.payload == CustomSearch.getmetadata('payload')
