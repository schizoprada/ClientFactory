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

# Create mock Request and Response for testing
@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.clone.return_value = MagicMock(spec=Request)
    return request

@pytest.fixture
def mock_response():
    response = MagicMock(spec=Response)
    response.json.return_value = {"data": "test_value", "items": ["item1", "item2"]}
    return response

def test_preprocess_decorator(mock_request):
    """Test preprocess decorator with method decorator"""
    def add_header(request):
        return request.clone(headers={"X-Test": "value"})

    # Test the transform function separately
    result = add_header(mock_request)
    mock_request.clone.assert_called_once_with(headers={"X-Test": "value"})

    # Test the decorator
    @get("test")
    def test_method():
        pass

    decorated = preprocess(add_header)(test_method)
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.preprocess == add_header

def test_postprocess_decorator(mock_response):
    """Test postprocess decorator with method decorator"""
    def extract_data(response):
        return response.json()["data"]

    # Test the transform function separately
    result = extract_data(mock_response)
    assert result == "test_value"

    # Test the decorator
    @get("test")
    def test_method():
        pass

    decorated = postprocess(extract_data)(test_method)
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.postprocess == extract_data

def test_transform_request(mock_request):
    """Test transformrequest decorator"""
    transform_func = lambda req: req.clone(headers={"X-API-KEY": "abc123"})

    @get("test")
    def test_method():
        pass

    # Then apply the transform decorator
    decorated = transformrequest(transform_func)(test_method)

    # Check that the transform function was stored as preprocess
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.preprocess == transform_func

    # Test the transform function
    result = transform_func(mock_request)
    mock_request.clone.assert_called_once_with(headers={"X-API-KEY": "abc123"})

def test_transform_response(mock_response):
    """Test transformresponse decorator"""
    transform_func = lambda resp: resp.json()["items"]

    @get("test")
    def test_method():
        pass

    # Then apply the transform decorator
    decorated = transformresponse(transform_func)(test_method)

    # Check that the transform function was stored as postprocess
    assert hasattr(decorated, '_methodconfig')
    assert decorated._methodconfig.postprocess == transform_func

    # Test the transform function
    result = transform_func(mock_response)
    assert result == ["item1", "item2"]

def test_preprocess_as_function(mock_request):
    """Test using preprocess as a function decorator"""
    @preprocess()  # Note: need to call it as a decorator function
    def add_header(request):
        return request.clone(headers={"X-Test": "value"})

    # Now add_header is decorated, pass the mock_request to it
    result = add_header(mock_request)
    mock_request.clone.assert_called_once_with(headers={"X-Test": "value"})

def test_postprocess_as_function(mock_response):
    """Test using postprocess as a function decorator"""
    @postprocess()  # Note: need to call it as a decorator function
    def extract_data(response):
        return response.json()["data"]

    # Now extract_data is decorated, pass the mock_response to it
    result = extract_data(mock_response)
    assert result == "test_value"  # Because mock_response.json() returns {"data": "test_value"}
