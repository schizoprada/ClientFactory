# ~/ClientFactory/tests/test_search_parameter_processing.py
import pytest
from clientfactory.clients.search.core import Parameter, ParameterType

def test_parameter_basic():
    """Test basic Parameter initialization and mapping"""
    p = Parameter(name="test")
    assert p.map("value") == {"test": "value"}

def test_parameter_process():
    """Test Parameter process functionality"""
    p = Parameter(
        name="page",
        process=lambda x: f"p:{x}",
        type=int,
        default=1
    )
    assert p.map(5) == {"page": "p:5"}

def test_parameter_process_error_handling():
    """Test process error handling with raisefor"""
    # Should raise
    p1 = Parameter(
        name="test",
        process=lambda x: x/0,  # Will raise ZeroDivisionError
        raisefor=['process']
    )
    with pytest.raises(ValueError):
        p1.map(10)

    # Should not raise
    p2 = Parameter(
        name="test",
        process=lambda x: x/0,
        raisefor=[]
    )
    result = p2.map(10)
    assert result == {"test": 10}  # Original value preserved on error

def test_parameter_type_validation():
    """Test type validation and enforcement"""
    # Should raise
    with pytest.raises(ValueError, match="Exception enforcing parameter type"):
        Parameter(
            name="test",
            type=int,
            default="not_an_int",
            raisefor=['type']
        )

    # Should not raise
    p2 = Parameter(
        name="test",
        type=int,
        default="not_an_int",
        raisefor=[]
    )
    assert p2.default == "not_an_int"  # Default remains unchanged when not raising

def test_parameter_map_with_none():
    """Test Parameter mapping with None value"""
    p = Parameter(
        name="page",
        default=1,
        type=int,
        process=lambda x: f"p:{x}"
    )
    assert p.map(None) == {"page": "p:1"}  # Should use default


def test_parameter_with_defaults():
    """Test Parameter with default values"""
    p = Parameter(
        name="page",
        default=1,
        process=lambda x: f"p:{x}",
        type=int
    )
    assert p.map(p.default) == {"page": "p:1"}

def test_parameter_chained_operations():
    """Test type conversion and processing chain"""
    p = Parameter(
        name="page",
        type=int,
        process=lambda x: f"p:{x*2}",  # Double the page number
        default="1"  # String that should be converted to int
    )
    assert p.map(5) == {"page": "p:10"}

def test_parameter_type_conversion():
    """Test automatic type conversion during validation"""
    p = Parameter(name="test", type=int)
    assert p.validate("123")  # Should accept string that can be converted
    assert not p.validate("abc")  # Should reject invalid conversion

def test_parameter_required():
    """Test required parameter behavior"""
    p = Parameter(name="test", required=True)
    # Note: actual required checking happens in Payload.validate()
    assert p.required == True

def test_parameter_paramtype():
    """Test parameter type enumeration"""
    p = Parameter(name="test", paramtype=ParameterType.QUERY)
    assert p.paramtype == ParameterType.QUERY

@pytest.mark.parametrize("input_val,expected", [
    (1, {"page": "p:1"}),
    ("2", {"page": "p:2"}),
    (None, {"page": "p:1"}),  # Should use default
])
def test_parameter_various_inputs(input_val, expected):
    """Test Parameter with various input types"""
    p = Parameter(
        name="page",
        default=1,
        type=int,
        process=lambda x: f"p:{x}"
    )
    # Use default if input is None
    val = p.default if input_val is None else input_val
    assert p.map(val) == expected
