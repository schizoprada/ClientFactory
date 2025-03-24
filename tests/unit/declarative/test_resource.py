# ~/ClientFactory/tests/unit/declarative/test_resource.py
import pytest
from clientfactory.declarative.resource import (
    DeclarativeResource, resource
)
from clientfactory.declarative.decorators import declarativemethod

def test_declarative_resource_basic():
    """Test basic DeclarativeResource functionality"""
    class TestResource(DeclarativeResource):
        path = "/test"
        name = "test_resource"

    assert TestResource.getmetadata('path') == "/test"
    assert TestResource.getmetadata('name') == "test_resource"

def test_resource_path_resolution():
    """Test path resolution for nested resources"""
    class Parent(DeclarativeResource):
        path = "/parent"

        @resource
        class Child:
            path = "child"

            @resource
            class GrandChild:
                path = "grandchild"

    child = Parent.getnestedresources()['child']
    grandchild = child.getnestedresources()['grandchild']

    assert child.getfullpath() == "/parent/child"
    assert grandchild.getfullpath() == "/parent/child/grandchild"

def test_resource_decorator():
    """Test @resource decorator"""
    @resource(path="/test", name="test_resource")
    class Test:
        pass

    assert issubclass(Test, DeclarativeResource)
    assert Test.getmetadata('path') == "/test"
    assert Test.getmetadata('name') == "test_resource"


def test_resource_methods():
    """Test resource method handling"""
    class TestResource(DeclarativeResource):
        @declarativemethod
        def test_method(self):
            pass

    methods = TestResource.getmethods()
    assert 'test_method' in methods
