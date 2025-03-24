# ~/ClientFactory/tests/unit/decorators/test_validation.py
"""
Unit tests for validation decorators
"""
import pytest
from unittest.mock import MagicMock, patch

from clientfactory.decorators.validation import ValidationError, validateinput, validateoutput
from clientfactory.decorators.method import get, post
from clientfactory.core.response import Response

@pytest.fixture
def mock_response():
    response = MagicMock(spec=Response)
    response.json.return_value = {
        "status": "ok",
        "items": ["item1", "item2"]
    }
    return response

class TestClass:
    """Test class for testing class methods with decorators"""

    @validateinput(lambda data: data)
    def method(self, **kwargs):
        return kwargs

    @validateinput(lambda data: {"name": data.get("name", "").upper()} if "name" in data else data)
    def transform_method(self, **kwargs):
        return kwargs

    @post("users")
    @validateinput(lambda data: data if "name" in data else {})
    def create_user(self, **data):
        return data


def test_validateinput_basic():
    """Test validateinput decorator basic functionality"""
    def validator(data):
        if 'name' not in data:
            raise ValidationError("Name is required")
        return data

    # Create a test class instance with decorated method
    class TestObj:
        @validateinput(validator)
        def test_method(self, **kwargs):
            return kwargs

    obj = TestObj()

    # Test with valid input
    result = obj.test_method(name="test")
    assert result == {"name": "test"}

    # Test with invalid input
    with pytest.raises(ValidationError):
        obj.test_method(email="test@example.com")


def test_validateinput_transformation():
    """Test validateinput decorator with input transformation"""
    def validator(data):
        # Transform data by uppercasing name
        if 'name' in data:
            data['name'] = data['name'].upper()
        return data

    # Create a test class instance with decorated method
    class TestObj:
        @validateinput(validator)
        def test_method(self, **kwargs):
            return kwargs

    obj = TestObj()

    # Test transformation
    result = obj.test_method(name="test")
    assert result == {"name": "TEST"}


def test_validateinput_with_method():
    """Test validateinput with HTTP method decorator"""
    def validator(data):
        if 'name' not in data:
            raise ValidationError("Name is required")
        return data

    # Create a class with a decorated method
    class TestAPI:
        @validateinput(validator)
        @post("users")
        def create_user(self, **data):
            return data

    api = TestAPI()

    # Test with valid input
    with patch('clientfactory.core.resource.Resource._createmethod'):
        result = api.create_user(name="test")
        assert result == {"name": "test"}

    # Test with invalid input
    with pytest.raises(ValidationError):
        api.create_user(email="test@example.com")


def test_validateoutput_basic(mock_response):
    """Test validateoutput decorator"""
    def validator(response):
        data = response.json()
        if 'status' not in data:
            raise ValidationError("Missing status field")
        return data

    @get("test")
    def test_method():
        pass

    # Then apply the validateoutput decorator
    decorated = validateoutput(validator)(test_method)

    # Check that validator was stored as postprocess
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.postprocess == validator

    # Test the validator
    result = validator(mock_response)
    assert result == {"status": "ok", "items": ["item1", "item2"]}

def test_validateoutput_with_method(mock_response):
    """Test validateoutput with HTTP method decorator"""
    def validator(response):
        data = response.json()
        if 'items' not in data:
            raise ValidationError("Missing items field")
        return data['items']

    @get("items")
    def test_method():
        pass

    # Then apply the validateoutput decorator
    decorated = validateoutput(validator)(test_method)

    # Check that validator was stored as postprocess
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.postprocess == validator

    # Test the validator
    result = validator(mock_response)
    assert result == ["item1", "item2"]
