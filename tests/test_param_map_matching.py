# ~/ClientFactory/tests/test_param_map_matching.py
import pytest
from fuzzywuzzy import fuzz
from clientfactory.clients.search.core import Parameter, ParameterType


TESTBRANDS = {
    'Rick Owens': 1,
    'Vetements': 2,
    'Raf Simons': 3,
    'Saint Laurent Paris': 4,
    'Yohji Yamamoto': 5
}

@pytest.fixture
def basic_param():
    return Parameter(
        name="test",
        mapinput=TESTBRANDS,
        raisefor=['map']
    )

@pytest.fixture
def fuzzy_param():
    return Parameter(
        name="test",
        mapinput=TESTBRANDS,
        fuzzymap=True,
        raisefor=['map']
    )

def test_exact_mapping(basic_param):
    """Test exact matches in mapinput"""
    assert basic_param.map("Rick Owens") == {"test": 1}
    assert basic_param.map("Vetements") == {"test": 2}

def test_exact_mapping_missing(basic_param):
    """Test missing exact matches"""
    with pytest.raises(ValueError, match="No mapping for value"):
        basic_param.map("NonExistent")

def test_fuzzy_mapping_basic():
    """Test basic fuzzy matching"""
    param = Parameter(
        name="test",
        mapinput=TESTBRANDS,
        fuzzymap=True,
        fuzzthreshold=70  # Lower threshold to catch 'yamamoto' -> 'Yohji Yamamoto' (73)
    )
    test_cases = [
        ("rick owen", 1),
        ("vetment", 2),
        ("raf simon", 3),
        ("saint laurent", 4),
        ("yamamoto", 5)
    ]
    for input_val, expected in test_cases:
        assert param.map(input_val) == {"test": expected}


def test_fuzzy_mapping_methods():
    """Test different fuzzy matching methods"""
    test_cases = [
        ('ratio', 'RICK OWENS', 1),  # Case insensitive
        ('partial_ratio', 'rick', 1),  # Partial match
        ('token_sort_ratio', 'owens rick', 1),  # Word order
        ('token_set_ratio', 'rick drkshdw owens', 1)  # Extra words
    ]

    for method, input_val, expected in test_cases:
        param = Parameter(
            name="test",
            mapinput=TESTBRANDS,
            fuzzymap=True,
            fuzzmethod=method
        )
        assert param.map(input_val) == {"test": expected}

def test_fuzzy_threshold():
    """Test threshold behavior"""
    param = Parameter(
        name="test",
        mapinput=TESTBRANDS,
        fuzzymap=True,
        fuzzthreshold=95,  # Very high threshold
        raisefor=['map']
    )

    # Should fail with high threshold
    with pytest.raises(ValueError):
        param.map("rik")

    # Lower threshold should work
    param.fuzzthreshold = 60
    param.fuzzmethod = 'partial_ratio'  # Better for short strings
    assert param.map("rik") == {"test": 1}

def test_non_string_values():
    """Test handling of non-string values"""
    param = Parameter(
        name="test",
        mapinput={1: "a", 2: "b"},
        fuzzymap=True,
        raisefor=['map']  # Add raisefor
    )

    # Exact matches should work
    assert param.map(1) == {"test": "a"}

    # Non-string values shouldn't attempt fuzzy matching
    with pytest.raises(ValueError):
        param.map(3)

def test_empty_mapinput():
    """Test behavior with empty mapinput"""
    param = Parameter(
        name="test",
        fuzzymap=True
    )

    # Should pass through value when no mapping defined
    assert param.map("anything") == {"test": "anything"}

def test_combined_processing():
    """Test fuzzy mapping combined with process function"""
    param = Parameter(
        name="test",
        mapinput=TESTBRANDS,
        fuzzymap=True,
        process=lambda x: f"ID:{x}"
    )

    assert param.map("rick owen") == {"test": "ID:1"}

def test_default_value_mapping():
    """Test mapping with default values"""
    param = Parameter(
        name="test",
        mapinput=TESTBRANDS,
        fuzzymap=True,
        default="Rick Owens"
    )

    assert param.map(None) == {"test": 1}

def test_case_sensitivity():
    """Test case sensitivity in matching"""
    param = Parameter(
        name="test",
        mapinput=TESTBRANDS,
        fuzzymap=True
    )

    variations = [
        "RICK OWENS",
        "rick owens",
        "Rick owens",
        "rIcK oWeNs"
    ]

    for var in variations:
        assert param.map(var) == {"test": 1}

def test_multi_word_handling():
    """Test handling of multi-word strings"""
    param = Parameter(
        name="test",
        mapinput=TESTBRANDS,
        fuzzymap=True,
        fuzzmethod='token_set_ratio'  # Better for scrambled words
    )

    test_cases = [
        ("laurent saint paris", 4),
        ("saint laurent", 4),
        ("paris saint laurent", 4)
    ]
    for input_val, expected in test_cases:
        assert param.map(input_val) == {"test": expected}, f"Failed on input: {input_val}"
