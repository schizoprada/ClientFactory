# ~/ClientFactory/tests/unit/decorators/test_transform.py
"""
Unit tests for transform decorators
"""
import pytest
from unittest.mock import MagicMock

from clientfactory.decorators.transform import preprocess, postprocess, transformrequest, transformresponse
from clientfactory.decorators.method import get, post
from clientfactory.core.request import Request, RequestMethod
from clientfactory.core.response import Response


def test_preprocess_decorator():
    """Test preprocess decorator with method decorator"""
    def add_header(request):
        return request.clone(headers={"X-Test": "value"})

    # Apply the get decorator first
    @get("test")
    class TestMethod:
        pass

    # Then apply the preprocess decorator
    decorated = preprocess(add_header)(TestMethod)

    # Check that the preprocess function was stored
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.preprocess == add_header


def test_postprocess_decorator():
    """Test postprocess decorator with method decorator"""
    def extract_data(response):
        return response.json()["data"]

    # Apply the get decorator first
    @get("test")
    class TestMethod:
        pass

    # Then apply the postprocess decorator
    decorated = postprocess(extract_data)(TestMethod)

    # Check that the postprocess function was stored
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.postprocess == extract_data


def test_transform_request():
    """Test transformrequest decorator"""
    transform_func = lambda req: req.clone(headers={"X-API-KEY": "abc123"})

    # Apply the get decorator first
    @get("test")
    class TestMethod:
        pass

    # Then apply the transform decorator
    decorated = transformrequest(transform_func)(TestMethod)

    # Check that the transform function was stored as preprocess
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.preprocess == transform_func

    # Create a mock request to test the transformation
    mock_request = MagicMock(spec=Request)
    mock_request.clone.return_value = "transformed_request"

    # Apply the transformation
    result = transform_func(mock_request)

    # Check that it works correctly
    mock_request.clone.assert_called_once_with(headers={"X-API-KEY": "abc123"})
    assert result == "transformed_request"


def test_transform_response():
    """Test transformresponse decorator"""
    transform_func = lambda resp: resp.json()["items"]

    # Apply the get decorator first
    @get("test")
    class TestMethod:
        pass

    # Then apply the transform decorator
    decorated = transformresponse(transform_func)(TestMethod)

    # Check that the transform function was stored as postprocess
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.postprocess == transform_func

    # Create a mock response to test the transformation
    mock_response = MagicMock(spec=Response)
    mock_response.json.return_value = {"items": ["item1", "item2"]}

    # Apply the transformation
    result = transform_func(mock_response)

    # Check that it works correctly
    assert result == ["item1", "item2"]


def test_preprocess_as_function():
    """Test using preprocess as a function decorator"""
    @preprocess
    def add_header(request):
        return request.clone(headers={"X-Test": "value"})

    # Create a mock request for testing
    mock_request = MagicMock(spec=Request)
    mock_request.clone.return_value = "modified_request"

    # Call the decorated function
    result = add_header(mock_request)

    # Check that it works correctly
    mock_request.clone.assert_called_once_with(headers={"X-Test": "value"})
    assert result == "modified_request"


def test_postprocess_as_function():
    """Test using postprocess as a function decorator"""
    @postprocess
    def extract_data(response):
        return response.json()["data"]

    # Create a mock response for testing
    mock_response = MagicMock(spec=Response)
    mock_response.json.return_value = {"data": "test_value"}

    # Call the decorated function
    result = extract_data(mock_response)

    # Check that it works correctly
    assert result == "test_value"
