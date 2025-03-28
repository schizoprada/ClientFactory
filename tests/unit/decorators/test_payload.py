# ~/ClientFactory/tests/unit/decorators/test_payload.py
"""Tests for payload decorator"""
import pytest
from datetime import datetime
from clientfactory.decorators.payload import (
    payload, EMPTY, name, type, default, required,
    choices, transform, description, validate,
    strparam, numparam, boolparam, arrayparam, dateparam,
    PT
)
from clientfactory.core.payload import Payload

def test_basic_payload():
    """Test basic payload with empty params"""
    @payload
    class TestPayload:
        keyword -> EMPTY
        simple -> EMPTY

    payload_inst = TestPayload()
    assert isinstance(payload_inst, Payload)
    assert 'keyword' in payload_inst.parameters
    assert 'simple' in payload_inst.parameters
    assert payload_inst.parameters['keyword'].name == 'keyword'
    assert payload_inst.parameters['simple'].name == 'simple'

def test_param_settings():
    """Test parameter settings with -> syntax"""
    @payload
    class TestPayload:
        # Simple name override
        exclude -> name("excludeKeyword")

        # Multiple settings
        brand -> (
            name("brandId") |
            type(PT.ARRAY) |
            default([])
        )

        # Required with choices
        status -> required() | choices("active", "pending", "done")

    payload_inst = TestPayload()

    assert payload_inst.parameters['exclude'].name == 'excludeKeyword'
    assert payload_inst.parameters['brand'].name == 'brandId'
    assert payload_inst.parameters['brand'].type == PT.ARRAY
    assert payload_inst.parameters['status'].required is True
    assert payload_inst.parameters['status'].choices == ["active", "pending", "done"]

def test_type_helpers():
    """Test type helper functions"""
    @payload
    class TestPayload:
        name -> strparam()
        age -> numparam(18)
        active -> boolparam(True)
        tags -> arrayparam()
        created -> dateparam("%Y-%m-%d")

    payload_inst = TestPayload()

    assert payload_inst.parameters['name'].type == PT.STRING
    assert payload_inst.parameters['age'].type == PT.NUMBER
    assert payload_inst.parameters['age'].default == 18
    assert payload_inst.parameters['active'].type == PT.BOOLEAN
    assert payload_inst.parameters['active'].default is True
    assert payload_inst.parameters['tags'].type == PT.ARRAY

    # Test date handling
    assert payload_inst.parameters['created'].transform is not None
    valid_date = "2024-01-01"
    transformed = payload_inst.parameters['created'].transform(valid_date)
    assert isinstance(transformed, datetime)

def test_validation():
    """Test payload validation"""
    @payload
    class TestPayload:
        required -> name("required_field") | required()
        age -> numparam() | validate(lambda x: 0 <= x <= 120)
        choice -> choices("A", "B", "C") | default("A")

    payload_inst = TestPayload()

    # Should raise for missing required
    with pytest.raises(Exception):
        payload_inst.validate({})

    # Should validate age range
    with pytest.raises(Exception):
        payload_inst.validate({"required_field": "value", "age": 150})

    # Should work with valid data
    assert payload_inst.validate({
        "required_field": "value",
        "age": 25,
        "choice": "B"
    })

def test_transformations():
    """Test payload transformations"""
    @payload
    class TestPayload:
        # Number doubler
        number -> numparam() | transform(lambda x: x * 2)

        # Date parser
        date -> dateparam()

        # List joiner
        tags -> arrayparam() | transform(lambda x: ",".join(x))

    payload_inst = TestPayload()
    result = payload_inst.apply({
        "number": 5,
        "date": "2024-01-01",
        "tags": ["a", "b", "c"]
    })

    assert result["number"] == 10
    assert isinstance(result["date"], datetime)
    assert result["tags"] == "a,b,c"

def test_complex_payload():
    """Test complex payload configuration"""
    @payload
    class TestPayload:
        # Basic param
        simple -> EMPTY

        # String with validation
        name -> strparam() | required() | validate(lambda x: len(x) <= 50)

        # Number with range
        age -> (
            numparam(18) |
            validate(lambda x: 0 <= x <= 120) |
            description("User age between 0 and 120")
        )

        # Enum-like with default
        status -> (
            choices("active", "pending", "done") |
            default("pending") |
            description("Current status")
        )

        # Array with transform
        tags -> (
            arrayparam() |
            transform(lambda x: [t.lower() for t in x]) |
            description("Tags (converted to lowercase)")
        )

    payload_inst = TestPayload()
    result = payload_inst.apply({
        "name": "Test User",
        "age": 25,
        "tags": ["Tag1", "Tag2"]
    })

    assert result["status"] == "pending"  # default value
    assert result["tags"] == ["tag1", "tag2"]  # transformed
    assert payload_inst.parameters['age'].description == "User age between 0 and 120"
