# ~/ClientFactory/tests/unit/declarative/test_decorators.py
import pytest
from clientfactory.declarative.decorators import declarative, declarativemethod, container
from clientfactory.declarative.base import DeclarativeComponent, DeclarativeContainer

def test_declarative_decorator_basic():
    """Test @declarative with no arguments"""
    @declarative
    class Test:
        value = "test"

    assert isinstance(Test, type)
    assert issubclass(Test, DeclarativeComponent)
    assert Test.getmetadata('value') == "test"

def test_declarative_decorator_with_metadata():
    """Test @declarative with metadata"""
    @declarative(metadata={'key': 'value'})
    class Test:
        pass

    assert Test.getmetadata('key') == 'value'

def test_declarative_method():
    """Test @declarativemethod functionality"""
    class Test:
        @declarativemethod
        def method(self):
            pass

        @declarativemethod(key='value')
        def method_with_meta(self):
            pass

    assert hasattr(Test.method, '__declarativemethod__')
    assert hasattr(Test.method, '__metadata__')
    assert Test.method_with_meta.__metadata__['key'] == 'value'

def test_container_decorator():
    """Test @container decorator"""
    @container
    class Test:
        value = "test"

        @declarativemethod
        def method(self):
            pass

        class Nested(DeclarativeComponent):
            pass

    assert issubclass(Test, DeclarativeContainer)
    assert 'methods' in Test.__metadata__
    assert 'components' in Test.__metadata__
    assert Test.getmetadata('value') == "test"

def test_container_with_metadata():
    """Test @container with metadata"""
    @container(metadata={'key': 'value'})
    class Test:
        pass

    assert Test.getmetadata('key') == 'value'
