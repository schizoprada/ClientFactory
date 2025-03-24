# ~/ClientFactory/tests/unit/declarative/test_base.py
import pytest
from clientfactory.declarative.base import (
    DeclarativeMeta, DeclarativeComponent,
    DeclarativeContainer, isdeclarative,
    getclassmetadata, copymetadata
)
from clientfactory.declarative.decorators import declarativemethod

def test_declarative_meta_basic():
    """Test basic DeclarativeMeta functionality"""
    class TestComponent(DeclarativeComponent):
        attribute = "value"

    assert hasattr(TestComponent, '__metadata__')
    assert TestComponent.__metadata__['attribute'] == "value"

def test_declarative_component_inheritance():
    """Test metadata inheritance between components"""
    class Parent(DeclarativeComponent):
        parent_attr = "parent"

    class Child(Parent):
        child_attr = "child"

    assert Child.getmetadata('parent_attr') == "parent"
    assert Child.getmetadata('child_attr') == "child"

def test_declarative_container():
    """Test container functionality"""
    class Container(DeclarativeContainer):
        @declarativemethod
        def method(self):
            pass

        class NestedComponent(DeclarativeComponent):
            pass

    assert 'methods' in Container.__metadata__
    assert 'components' in Container.__metadata__
    assert 'method' in Container.__metadata__['methods']
    assert 'nestedcomponent' in Container.__metadata__['components']

def test_metadata_operations():
    """Test metadata manipulation methods"""
    class Test(DeclarativeComponent):
        attr = "value"

    Test.setmetadata('new', 'data')
    assert Test.hasmetadata('new')
    assert Test.getmetadata('new') == 'data'

    Test.updatemetdata({'more': 'stuff'})
    assert Test.getmetadata('more') == 'stuff'

    alldata = Test.getallmetadata()
    assert isinstance(alldata, dict)
    assert 'attr' in alldata

def test_isdeclarative():
    """Test isdeclarative utility function"""
    class Regular:
        pass

    class Declarative(DeclarativeComponent):
        pass

    assert not isdeclarative(Regular)
    assert isdeclarative(Declarative)

def test_metadata_copying():
    """Test metadata copying between classes"""
    class Source(DeclarativeComponent):
        pass

    # Set metadata directly rather than through attributes
    Source.setmetadata('a', 1)
    Source.setmetadata('b', 2)

    class Target(DeclarativeComponent):
        pass

    copymetadata(Source, Target, ['a'])
    assert Target.getmetadata('a') == 1
    assert not Target.hasmetadata('b')

def test_declarative_container_discovery():
    """Test container component discovery"""
    class Container(DeclarativeContainer):
        class Component(DeclarativeComponent):
            name = "mycomponent"

    assert "mycomponent" in Container.__metadata__['components']
