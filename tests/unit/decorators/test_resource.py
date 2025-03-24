# ~/ClientFactory/tests/unit/decorators/test_resource.py
"""
Unit tests for resource decorators
"""
import pytest
from unittest.mock import MagicMock

from clientfactory.decorators.resource import resource, subresource
from clientfactory.decorators.method import get, post
from clientfactory.core.resource import ResourceConfig
from clientfactory.core.request import RequestMethod

def test_resource_basic():
    """Test basic resource decorator usage"""
    @resource
    class TestResource:
        pass

    assert hasattr(TestResource, '_resourceconfig')
    config = TestResource._resourceconfig

    assert isinstance(config, ResourceConfig)
    assert config.name == 'TestResource'
    assert config.path == 'testresource'


def test_resource_with_path():
    """Test resource decorator with explicit path"""
    @resource(path="custom/path")
    class TestResource:
        pass

    assert hasattr(TestResource, '_resourceconfig')
    config = TestResource._resourceconfig

    assert config.path == 'custom/path'


def test_resource_with_path_attr():
    """Test resource decorator with class path attribute"""
    @resource
    class TestResource:
        path = "from-attribute"

    assert hasattr(TestResource, '_resourceconfig')
    config = TestResource._resourceconfig

    assert config.path == 'from-attribute'


def test_resource_with_name():
    """Test resource decorator with explicit name"""
    @resource(name="CustomName")
    class TestResource:
        pass

    assert hasattr(TestResource, '_resourceconfig')
    config = TestResource._resourceconfig

    assert config.name == 'CustomName'


def test_resource_with_methods():
    """Test resource with method decorators"""
    @resource
    class TestResource:
        @get("items")
        def list_items(self):
            pass

        @post("items")
        def create_item(self, **data):
            pass

    assert hasattr(TestResource, '_resourceconfig')
    config = TestResource._resourceconfig

    assert len(config.methods) == 2
    assert 'list_items' in config.methods
    assert 'create_item' in config.methods

    assert config.methods['list_items'].method == RequestMethod.GET
    assert config.methods['list_items'].path == 'items'

    assert config.methods['create_item'].method == RequestMethod.POST
    assert config.methods['create_item'].path == 'items'


def test_subresource():
    """Test subresource decorator"""
    @resource
    class ParentResource:
        @subresource
        class ChildResource:
            @get("items")
            def list_items(self):
                pass

    assert hasattr(ParentResource, '_resourceconfig')
    assert hasattr(ParentResource.ChildResource, '_resourceconfig')

    parent_config = ParentResource._resourceconfig
    child_config = ParentResource.ChildResource._resourceconfig

    assert parent_config.name == 'ParentResource'
    assert child_config.name == 'ChildResource'

    assert child_config.path == 'childresource'

    assert len(child_config.methods) == 1
    assert 'list_items' in child_config.methods
