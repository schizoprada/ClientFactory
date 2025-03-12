# ~/ClientFactory/src/clientfactory/clients/search/tests/test_nested_parameters.py
import pytest
from clientfactory.clients.search.core import Parameter, NestedParameter, Payload


def test_nested_parameter_basic():
    nested = NestedParameter(
        price=NestedParameter(
            min=Parameter(name="price.gte"),
            max=Parameter(name="price.lte")
        )
    )

    # Test nested dictionary format
    assert nested.validate({
        "price": {
            "min": 10,
            "max": 100
        }
    })

    # Test dot notation
    assert nested.validate({
        "price.min": 10,
        "price.max": 100
    })

def test_nested_parameter_mapping():
    nested = NestedParameter(
        price=NestedParameter(
            min=Parameter(name="price.gte"),
            max=Parameter(name="price.lte")
        )
    )

    # Test nested mapping
    nested_result = nested.map({
        "price": {
            "min": 10,
            "max": 100
        }
    })
    assert nested_result == {
        "price": {
            "price.gte": 10,
            "price.lte": 100
        }
    }

    # Test dot notation mapping
    dot_result = nested.map({
        "price.min": 10,
        "price.max": 100
    })
    assert dot_result == {
        "price.gte": 10,
        "price.lte": 100
    }

def test_mixed_notation():
    nested = NestedParameter(
        price=NestedParameter(
            min=Parameter(name="price.gte"),
            max=Parameter(name="price.lte")
        ),
        category=Parameter(name="cat")
    )

    # Test mixed dot notation and nested structure
    result = nested.map({
        "price.min": 10,
        "category": "shoes"
    })

    assert result == {
        "price.gte": 10,
        "cat": "shoes"
    }
