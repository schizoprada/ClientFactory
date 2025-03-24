# ~/ClientFactory/tests/unit/decorators/test_method.py
"""
Unit tests for method decorators
"""
import pytest
from unittest.mock import MagicMock

from clientfactory.decorators.method import httpmethod, methodwithpayload, get, post, put, patch, delete
from clientfactory.core.request import RequestMethod, RM
from clientfactory.core.payload import Payload, Parameter


def test_httpmethod_basic():
    """Test the basic HTTP method decorator"""
    @httpmethod(RM.GET, "test/path")
    def test_method():
        pass

    assert hasattr(test_method, '_methodconfig')
    cfg = test_method._methodconfig

    assert cfg.name == 'test_method'
    assert cfg.method == RM.GET
    assert cfg.path == 'test/path'


def test_httpmethod_with_options():
    """Test HTTP method decorator with additional options"""
    def preprocess_func(request):
        return request

    def postprocess_func(response):
        return response

    @httpmethod(
        RM.POST,
        "test/path",
        preprocess=preprocess_func,
        postprocess=postprocess_func,
        description="Test description"
    )
    def test_method():
        """Method docstring"""
        pass

    assert hasattr(test_method, '_methodconfig')
    cfg = test_method._methodconfig

    assert cfg.method == RM.POST
    assert cfg.path == 'test/path'
    assert cfg.preprocess == preprocess_func
    assert cfg.postprocess == postprocess_func
    assert cfg.description == "Test description"


def test_get_decorator():
    """Test the GET method decorator"""
    @get("items/{id}")
    def get_item(id):
        pass

    assert hasattr(get_item, '_methodconfig')
    cfg = get_item._methodconfig

    assert cfg.method == RM.GET
    assert cfg.path == 'items/{id}'


def test_post_decorator():
    """Test the POST method decorator"""
    @post("items")
    def create_item(**data):
        pass

    assert hasattr(create_item, '_methodconfig')
    cfg = create_item._methodconfig

    assert cfg.method == RM.POST
    assert cfg.path == 'items'


def test_put_decorator():
    """Test the PUT method decorator"""
    @put("items/{id}")
    def update_item(id, **data):
        pass

    assert hasattr(update_item, '_methodconfig')
    cfg = update_item._methodconfig

    assert cfg.method == RM.PUT
    assert cfg.path == 'items/{id}'


def test_patch_decorator():
    """Test the PATCH method decorator"""
    @patch("items/{id}")
    def partial_update(id, **data):
        pass

    assert hasattr(partial_update, '_methodconfig')
    cfg = partial_update._methodconfig

    assert cfg.method == RM.PATCH
    assert cfg.path == 'items/{id}'


def test_delete_decorator():
    """Test the DELETE method decorator"""
    @delete("items/{id}")
    def delete_item(id):
        pass

    assert hasattr(delete_item, '_methodconfig')
    cfg = delete_item._methodconfig

    assert cfg.method == RM.DELETE
    assert cfg.path == 'items/{id}'


def test_method_with_payload():
    """Test methodwithpayload helper"""
    payload = Payload(
        name=Parameter(required=True),
        email=Parameter()
    )

    post_with_payload = methodwithpayload(post, payload)

    @post_with_payload("users")
    def create_user(**data):
        pass

    assert hasattr(create_user, '_methodconfig')
    cfg = create_user._methodconfig

    assert cfg.method == RM.POST
    assert cfg.path == 'users'
    assert cfg.payload is payload
