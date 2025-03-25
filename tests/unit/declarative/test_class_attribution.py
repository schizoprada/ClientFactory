# ~/ClientFactory/tests/unit/declarative/test_class_attribution.py
from __future__ import annotations
import pytest
from dataclasses import dataclass

from clientfactory.declarative import (
    DeclarativeComponent, DeclarativeContainer,
    declarative, declarativemethod
)

def test_basic_attribute_processing():
    """Test basic attribute processing in DeclarativeComponent"""
    class TestComponent(DeclarativeComponent):
        normal_attr = "value"
        number_attr = 42
        list_attr = [1, 2, 3]
        dict_attr = {"key": "value"}
        _private = "private"

        @property
        def prop(self):
            return "prop"

        def method(self):
            pass

    # Normal attributes should be in metadata
    assert 'normal_attr' in TestComponent.__metadata__
    assert 'number_attr' in TestComponent.__metadata__
    assert 'list_attr' in TestComponent.__metadata__
    assert 'dict_attr' in TestComponent.__metadata__

    # These should not be in metadata
    assert '_private' not in TestComponent.__metadata__
    assert 'prop' not in TestComponent.__metadata__
    assert 'method' not in TestComponent.__metadata__

    # Values should match
    assert TestComponent.__metadata__['normal_attr'] == "value"
    assert TestComponent.__metadata__['number_attr'] == 42
    assert TestComponent.__metadata__['list_attr'] == [1, 2, 3]
    assert TestComponent.__metadata__['dict_attr'] == {"key": "value"}

def test_inheritance_processing():
    """Test metadata inheritance"""
    class Parent(DeclarativeComponent):
        parent_attr = "parent"
        shared_attr = "parent_value"

    class Child(Parent):
        child_attr = "child"
        shared_attr = "child_value"  # Override parent

    # Child should have both its own and parent's attributes
    assert 'parent_attr' in Child.__metadata__
    assert 'child_attr' in Child.__metadata__
    assert Child.__metadata__['parent_attr'] == "parent"
    assert Child.__metadata__['child_attr'] == "child"

    # Child's value should override parent's
    assert Child.__metadata__['shared_attr'] == "child_value"

def test_container_processing():
    """Test container-specific processing"""
    class Container(DeclarativeContainer):
        container_attr = "container"

        @declarativemethod
        def method(self):
            pass

        class Nested(DeclarativeComponent):
            nested_attr = "nested"

    # Should have normal attribute processing
    assert 'container_attr' in Container.__metadata__
    assert Container.__metadata__['container_attr'] == "container"

    # Should have methods container
    assert 'methods' in Container.__metadata__
    assert 'method' in Container.__metadata__['methods']

    # Should have components container
    assert 'components' in Container.__metadata__
    assert 'nested' in Container.__metadata__['components']

    # Nested component should have its attributes processed
    nested_component = Container.__metadata__['components']['nested']
    assert 'nested_attr' in nested_component.__metadata__
    assert nested_component.__metadata__['nested_attr'] == "nested"

def test_dataclass_handling():
    """Test handling of dataclass attributes"""
    @dataclass
    class Config:
        name: str
        value: int

    class TestComponent(DeclarativeComponent):
        config = Config("test", 42)

    # Dataclass instance should be stored as-is
    assert 'config' in TestComponent.__metadata__
    assert isinstance(TestComponent.__metadata__['config'], Config)
    assert TestComponent.__metadata__['config'].name == "test"
    assert TestComponent.__metadata__['config'].value == 42

def test_nested_container_inheritance():
    """Test nested container inheritance"""
    class ParentContainer(DeclarativeContainer):
        class ParentNested(DeclarativeComponent):
            parent_nested_attr = "parent"

    class ChildContainer(ParentContainer):
        class ChildNested(DeclarativeComponent):
            child_nested_attr = "child"

    # Both parent and child nested components should be registered
    assert 'parentnested' in ChildContainer.__metadata__['components']
    assert 'childnested' in ChildContainer.__metadata__['components']

    # Nested components should have their attributes
    parent_nested = ChildContainer.__metadata__['components']['parentnested']
    child_nested = ChildContainer.__metadata__['components']['childnested']

    assert parent_nested.__metadata__['parent_nested_attr'] == "parent"
    assert child_nested.__metadata__['child_nested_attr'] == "child"

def test_declarative_method_metadata():
    """Test declarative method metadata handling"""
    class TestContainer(DeclarativeContainer):
        @declarativemethod(description="test method")
        def test_method(self):
            pass

    # Method should be registered with metadata
    assert 'test_method' in TestContainer.__metadata__['methods']
    method = TestContainer.__metadata__['methods']['test_method']
    assert hasattr(method, '__metadata__')
    assert method.__metadata__['description'] == 'test method'
