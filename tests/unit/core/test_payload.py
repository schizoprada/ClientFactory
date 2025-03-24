# ~/ClientFactory/tests/unit/test_payload.py
"""
Tests for the core.payload module
"""
import pytest
from unittest.mock import MagicMock

from clientfactory.core.payload import (
    Parameter, ParameterType as PT, NestedParameter,
    Payload, PayloadBuilder, PayloadTemplate,
    ValidationError
)


# Tests for Parameter
def test_parameter_initialization():
    """Test parameter initialization with different configurations"""
    # Basic initialization
    param = Parameter()
    assert param.name is None
    assert param.type == PT.ANY
    assert not param.required

    # Full initialization
    param = Parameter(
        name="test",
        type=PT.STRING,
        required=True,
        default="default",
        description="A test parameter",
        choices=["one", "two", "three"]
    )
    assert param.name == "test"
    assert param.type == PT.STRING
    assert param.required
    assert param.default == "default"
    assert param.description == "A test parameter"
    assert param.choices == ["one", "two", "three"]


def test_parameter_validation():
    """Test parameter validation rules"""
    # Type validation
    string_param = Parameter(name="string", type=PT.STRING)
    assert string_param.validate("test")
    assert not string_param.validate(123)

    # Required validation
    required_param = Parameter(name="required", required=True)
    assert required_param.validate("test")
    with pytest.raises(ValidationError):
        required_param.validate(None)

    # Required with default
    required_with_default = Parameter(name="required_default", required=True, default="default")
    assert required_with_default.validate(None)

    # Choices validation
    choices_param = Parameter(name="choices", choices=["one", "two", "three"])
    assert choices_param.validate("one")
    assert not choices_param.validate("four")

    # Choices with required
    required_choices = Parameter(name="required_choices", required=True, choices=["one", "two", "three"])
    assert required_choices.validate("one")
    with pytest.raises(ValidationError):
        required_choices.validate("four")


def test_parameter_apply():
    """Test parameter application with transformation"""
    # Simple parameter
    param = Parameter(name="test", default="default")
    assert param.apply(None) == "default"
    assert param.apply("value") == "value"

    # Parameter with transform
    transform_param = Parameter(
        name="transform",
        transform=lambda x: x.upper()
    )
    assert transform_param.apply("test") == "TEST"

    # Parameter with validation and transform
    validated_transform = Parameter(
        name="validated",
        type=PT.STRING,
        required=True,
        transform=lambda x: x.upper()
    )
    assert validated_transform.apply("test") == "TEST"
    with pytest.raises(ValidationError):
        validated_transform.apply(123)


# Tests for NestedParameter
def test_nested_parameter():
    """Test nested parameter functionality"""
    nested = NestedParameter(
        name="user",
        children={
            "name": Parameter(type=PT.STRING, required=True),
            "age": Parameter(type=PT.NUMBER, default=18),
            "email": Parameter(type=PT.STRING)
        }
    )

    # Validate a complete object
    data = {
        "name": "John",
        "age": 25,
        "email": "john@example.com"
    }
    assert nested.validate(data)

    # Validate with missing optional field
    data = {
        "name": "John",
        "age": 25
    }
    assert nested.validate(data)

    # Validate with missing required field
    data = {
        "age": 25,
        "email": "john@example.com"
    }
    with pytest.raises(ValidationError):
        nested.validate(data)

    # Apply transformation
    data = {
        "name": "John",
        "age": 25
    }
    result = nested.apply(data)
    assert result["name"] == "John"
    assert result["age"] == 25
    assert "email" not in result


# Tests for Payload
def test_payload_initialization():
    """Test payload initialization with parameters"""
    # Create payload with explicit parameter names
    payload = Payload(
        query=Parameter(name="q"),
        limit=Parameter(name="count")
    )

    assert "query" in payload.parameters
    assert "limit" in payload.parameters
    assert payload.parameters["query"].name == "q"
    assert payload.parameters["limit"].name == "count"

    # Create payload with automatic parameter names
    payload = Payload(
        query=Parameter(),
        limit=Parameter()
    )

    assert "query" in payload.parameters
    assert "limit" in payload.parameters
    assert payload.parameters["query"].name == "query"
    assert payload.parameters["limit"].name == "limit"

    # Create payload with mixed parameter types
    payload = Payload(
        query=Parameter(),
        filters=NestedParameter(
            children={
                "min": Parameter(type=PT.NUMBER),
                "max": Parameter(type=PT.NUMBER)
            }
        ),
        static_value="always included"
    )

    assert "query" in payload.parameters
    assert "filters" in payload.parameters
    assert "static_value" in payload.static
    assert payload.parameters["filters"].children["min"].type == PT.NUMBER


def test_payload_validation():
    """Test payload validation rules"""
    payload = Payload(
        query=Parameter(required=True),
        limit=Parameter(type=PT.NUMBER, default=10)
    )

    # Valid data
    assert payload.validate({"query": "search term"})
    assert payload.validate({"query": "search term", "limit": 20})

    # Unknown parameter
    with pytest.raises(ValidationError):
        payload.validate({"query": "search term", "unknown": "value"})

    # Missing required parameter
    with pytest.raises(ValidationError):
        payload.validate({"limit": 20})

    # Type validation
    with pytest.raises(ValidationError):
        payload.validate({"query": "search term", "limit": "twenty"})


def test_payload_apply():
    """Test payload application with transformation"""
    payload = Payload(
        query=Parameter(required=True),
        limit=Parameter(type=PT.NUMBER, default=10),
        sort=Parameter(choices=["asc", "desc"], default="asc")
    )

    # Basic application
    result = payload.apply({"query": "search term"})
    assert result["query"] == "search term"
    assert result["limit"] == 10
    assert result["sort"] == "asc"

    # Application with overrides
    result = payload.apply({"query": "search term", "limit": 20, "sort": "desc"})
    assert result["query"] == "search term"
    assert result["limit"] == 20
    assert result["sort"] == "desc"


def test_payload_attribute_access():
    """Test accessing parameters as attributes on the payload"""
    payload = Payload(
        query=Parameter(),
        limit=Parameter(name="count")
    )

    # Access parameters via attributes
    assert payload.query.name == "query"
    assert payload.limit.name == "count"

    # Attribute error for non-existent parameter
    with pytest.raises(AttributeError):
        payload.nonexistent


# Tests for PayloadBuilder
def test_payload_builder():
    """Test payload builder functionality"""
    builder = PayloadBuilder()

    # Add parameters
    builder.addparam("query", type=PT.STRING, required=True)
    builder.addparam("limit", type=PT.NUMBER, default=10)

    # Add nested parameter
    builder.addnestedparam(
        "filters",
        children={
            "min": {"type": PT.NUMBER},
            "max": {"type": PT.NUMBER}
        }
    )

    # Add static values
    builder.addstatic(version="1.0")

    # Build payload
    payload = builder.build()

    # Verify payload
    assert "query" in payload.parameters
    assert "limit" in payload.parameters
    assert "filters" in payload.parameters
    assert "version" in payload.static
    assert payload.parameters["query"].required
    assert payload.parameters["limit"].default == 10
    assert "min" in payload.parameters["filters"].children
    assert "max" in payload.parameters["filters"].children


# Tests for PayloadTemplate
def test_payload_template():
    """Test payload template functionality"""
    template = PayloadTemplate(
        parameters={
            "query": {"type": PT.STRING.value, "required": True},
            "limit": {"type": PT.NUMBER.value, "default": 10}
        },
        static={"version": "1.0"}
    )

    # Build from template
    payload = template.build()

    # Verify payload
    assert "query" in payload.parameters
    assert "limit" in payload.parameters
    assert "version" in payload.static
    assert payload.parameters["query"].required
    assert payload.parameters["limit"].default == 10

    # Build with overrides
    payload = template.build(
        query={"default": "default search"},
        limit=Parameter(default=20)
    )

    # Verify overrides
    assert payload.parameters["query"].default == "default search"
    assert payload.parameters["limit"].default == 20

    # Test template extension
    extended = template.extend(
        parameters={
            "sort": {"choices": ["asc", "desc"], "default": "asc"}
        },
        static={"api_version": "2.0"}
    )

    # Build from extended template
    payload = extended.build()

    # Verify extended payload
    assert "query" in payload.parameters
    assert "limit" in payload.parameters
    assert "sort" in payload.parameters
    assert "version" in payload.static
    assert "api_version" in payload.static
    assert payload.parameters["sort"].choices == ["asc", "desc"]
