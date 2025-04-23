# ~/ClientFactory/tests/unit/core/test_transient_params.py
import pytest
import json
from clientfactory.core.payload import (
    Parameter, Payload, ValidationError,
    ParameterType as PT, ConditionalParameter
)

def test_basic_transient_param():
    """Test basic transient parameter behavior"""
    payload = Payload(
        visible=Parameter(default="visible"),
        hidden=Parameter(default="hidden", transient=True)
    )

    result = payload.apply({})
    assert "visible" in result
    assert "hidden" not in result
    assert result["visible"] == "visible"

def test_transient_with_transform():
    """Test transient parameter with transformation"""
    payload = Payload(
        helper=Parameter(
            default=100,
            transform=lambda x: f"value>={x}",
            transient=True
        ),
        filter=ConditionalParameter(
            dependencies=('helper',),
            conditions={'value': lambda h: [h]}
        )
    )

    result = payload.apply({})
    assert "helper" not in result
    assert result["filter"] == ["value>=100"]

class TestPriceFilterExample:
    """Tests using price filter example case"""

    @pytest.fixture
    def price_payload(self):
        return Payload(
            minprice=Parameter(
                default=0,
                transform=lambda x: f"price>={x}",
                transient=True
            ),
            maxprice=Parameter(
                default=1000,
                transform=lambda x: f"price<={x}",
                transient=True
            ),
            filters=ConditionalParameter(
                dependencies=('minprice', 'maxprice'),
                conditions={
                    'value': lambda min_, max_: json.dumps([min_, max_])
                }
            )
        )

    def test_default_values(self, price_payload):
        """Test payload with default values"""
        result = price_payload.apply({})
        assert "minprice" not in result
        assert "maxprice" not in result
        assert "filters" in result

        filters = json.loads(result["filters"])
        assert filters == ["price>=0", "price<=1000"]

    def test_custom_values(self, price_payload):
        """Test payload with custom price values"""
        result = price_payload.apply({
            "minprice": 100,
            "maxprice": 500
        })
        assert "minprice" not in result
        assert "maxprice" not in result
        assert "filters" in result

        filters = json.loads(result["filters"])
        assert filters == ["price>=100", "price<=500"]

def test_transient_required_param():
    """Test transient parameter that is required"""
    payload = Payload(
        helper=Parameter(
            required=True,
            transient=True
        ),
        dependent=ConditionalParameter(
            dependencies=('helper',),
            conditions={'value': lambda h: h.upper()}
        )
    )

    # Should still validate required even though transient
    with pytest.raises(ValidationError):
        payload.apply({})

    # Should work with valid input
    result = payload.apply({"helper": "test"})
    assert "helper" not in result
    assert result["dependent"] == "TEST"

def test_mixed_params():
    """Test mix of transient and normal parameters"""
    payload = Payload(
        normal1=Parameter(default="n1"),
        trans1=Parameter(default="t1", transient=True),
        normal2=Parameter(default="n2"),
        trans2=Parameter(default="t2", transient=True)
    )

    result = payload.apply({})
    assert set(result.keys()) == {"normal1", "normal2"}
    assert result["normal1"] == "n1"
    assert result["normal2"] == "n2"

def test_transient_with_name():
    """Test transient parameter with custom name"""
    payload = Payload(
        helper=Parameter(
            name="different_name",
            default="value",
            transient=True
        )
    )

    result = payload.apply({})
    assert "helper" not in result
    assert "different_name" not in result

def test_transient_validation():
    """Test that transient parameters still undergo validation"""
    payload = Payload(
        helper=Parameter(
            type=PT.NUMBER,
            transient=True
        )
    )

    # Should still validate type
    with pytest.raises(ValidationError):
        payload.apply({"helper": "not a number"})

    # Should work with valid type
    result = payload.apply({"helper": 123})
    assert "helper" not in result

def test_conditional_on_multiple_transients():
    """Test conditional parameter depending on multiple transient parameters"""
    payload = Payload(
        t1=Parameter(default="A", transient=True),
        t2=Parameter(default="B", transient=True),
        t3=Parameter(default="C", transient=True),
        combined=ConditionalParameter(
            dependencies=('t1', 't2', 't3'),
            conditions={'value': lambda x, y, z: f"{x}-{y}-{z}"}
        )
    )

    result = payload.apply({})
    assert all(k not in result for k in ['t1', 't2', 't3'])
    assert result["combined"] == "A-B-C"

def test_nested_dependencies():
    """Test nested dependencies with transient parameters"""
    payload = Payload(
        t1=Parameter(default=5, transient=True),
        t2=ConditionalParameter(
            dependencies=('t1',),
            conditions={'value': lambda x: x * 2},
            transient=True
        ),
        final=ConditionalParameter(
            dependencies=('t1', 't2'),
            conditions={'value': lambda x, y: x + y}
        )
    )

    result = payload.apply({})
    assert "t1" not in result
    assert "t2" not in result
    assert result["final"] == 15  # 5 + (5*2)
