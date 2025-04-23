# ~/ClientFactory/tests/unit/core/test_conditional_parameter.py
import pytest
from clientfactory.core.payload import (
    Parameter, ConditionalParameter, ValidationError,
    ParameterType as PT, Payload
)

def test_basic_initialization():
    """Test basic ConditionalParameter initialization"""
    param = ConditionalParameter(
        dependencies=('a', 'b'),
        conditions={'value': lambda a, b: a + b}
    )
    assert param.dependencies == ('a', 'b')
    assert 'value' in param.conditions

def test_invalid_condition_type():
    """Test that invalid condition types raise ValidationError"""
    with pytest.raises(ValidationError, match="Invalid condition types"):
        ConditionalParameter(
            dependencies=('a',),
            conditions={'invalid': lambda x: x}
        )

def test_missing_context():
    """Test that applying without context raises ValidationError"""
    param = ConditionalParameter(
        dependencies=('a',),
        conditions={'value': lambda a: a}
    )
    with pytest.raises(ValidationError, match="Context required"):
        param.apply("test")

def test_missing_dependency():
    """Test that missing dependency raises ValidationError"""
    param = ConditionalParameter(
        dependencies=('a', 'b'),
        conditions={'value': lambda a, b: a + b}
    )
    with pytest.raises(ValidationError, match="Missing required dependency"):
        param.apply("test", context={'a': 1})

class TestValueCondition:
    """Tests for the 'value' condition"""

    def test_value_computation(self):
        """Test basic value computation"""
        param = ConditionalParameter(
            dependencies=('a', 'b'),
            conditions={'value': lambda a, b: a + b}
        )
        result = param.apply(None, context={'a': 1, 'b': 2})
        assert result == 3

    def test_value_with_type_validation(self):
        """Test value computation with type validation"""
        param = ConditionalParameter(
            dependencies=('a', 'b'),
            conditions={'value': lambda a, b: str(a + b)},
            type=PT.STRING
        )
        result = param.apply(None, context={'a': 1, 'b': 2})
        assert result == "3"
        assert isinstance(result, str)

class TestIncludeCondition:
    """Tests for the 'include' condition"""

    def test_include_true(self):
        """Test parameter inclusion"""
        param = ConditionalParameter(
            dependencies=('flag',),
            conditions={'include': lambda flag: flag}
        )
        result = param.apply("test", context={'flag': True})
        assert result == "test"

    def test_include_false(self):
        """Test parameter exclusion"""
        param = ConditionalParameter(
            dependencies=('flag',),
            conditions={'include': lambda flag: flag}
        )
        result = param.apply("test", context={'flag': False})
        assert result is None

class TestRequiredCondition:
    """Tests for the 'required' condition"""

    def test_required_true(self):
        """Test required=True condition"""
        param = ConditionalParameter(
            dependencies=('flag',),
            conditions={'required': lambda flag: flag},
            type=PT.STRING
        )
        with pytest.raises(ValidationError, match="is required"):
            param.apply(None, context={'flag': True})

    def test_required_false(self):
        """Test required=False condition"""
        param = ConditionalParameter(
            dependencies=('flag',),
            conditions={'required': lambda flag: flag}
        )
        result = param.apply(None, context={'flag': False})
        assert result is None

class TestValidateCondition:
    """Tests for the 'validate' condition"""

    def test_validate_success(self):
        """Test successful validation"""
        param = ConditionalParameter(
            dependencies=('min', 'max'),
            conditions={
                'validate': lambda val, min_, max_: min_ <= val <= max_
            }
        )
        result = param.apply(5, context={'min': 0, 'max': 10})
        assert result == 5

    def test_validate_failure(self):
        """Test validation failure"""
        param = ConditionalParameter(
            dependencies=('min', 'max'),
            conditions={
                'validate': lambda val, min_, max_: min_ <= val <= max_
            }
        )
        with pytest.raises(ValidationError, match="Conditional validation failed"):
            param.apply(15, context={'min': 0, 'max': 10})

class TestMultipleConditions:
    """Tests for multiple conditions working together"""

    def test_combined_conditions(self):
        """Test multiple conditions working together"""
        param = ConditionalParameter(
            dependencies=('flag', 'min', 'max'),
            conditions={
                'include': lambda flag, *_: flag,
                'required': lambda flag, *_: flag,
                'validate': lambda val, _, min_, max_: min_ <= val <= max_,
                'value': lambda flag, min_, max_: min_ if flag else None
            },
            type=PT.NUMBER
        )

        # Test when flag is True
        result = param.apply(None, context={'flag': True, 'min': 0, 'max': 10})
        assert result == 0

        # Test when flag is False
        result = param.apply(None, context={'flag': False, 'min': 0, 'max': 10})
        assert result is None

class TestWithPayload:
    """Tests for ConditionalParameter within a Payload"""

    def test_payload_integration(self):
        """Test ConditionalParameter working within a Payload"""
        payload = Payload(
            keyword=Parameter(type=PT.STRING),
            brand=Parameter(type=PT.STRING),
            category=ConditionalParameter(
                dependencies=('keyword', 'brand'),
                conditions={
                    'required': lambda kw, brand: not kw and brand,
                    'value': lambda kw, brand: 'all' if not kw and brand else None,
                    'include': lambda kw, brand: not kw
                },
                type=PT.STRING
            )
        )

        # Test with keyword only
        result = payload.apply({
            'keyword': 'test',
            'brand': None,
            'category': None
        })
        assert 'category' not in result
        assert result['keyword'] == 'test'

        # Test with brand only (should set category='all')
        result = payload.apply({
            'keyword': None,
            'brand': 'nike',
            'category': None
        })
        assert result['category'] == 'all'
        assert result['brand'] == 'nike'

def test_inheritance():
    """Test that ConditionalParameter properly inherits from Parameter"""
    param = ConditionalParameter(
        dependencies=('a',),
        conditions={'value': lambda a: a},
        type=PT.STRING,
        required=True,
        description="test parameter"
    )

    assert isinstance(param, Parameter)
    assert param.type == PT.STRING
    assert param.required is True
    assert param.description == "test parameter"
