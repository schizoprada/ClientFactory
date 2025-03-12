# ~/ClientFactory/tests/test_utils_requests_iterator.py
import pytest
from unittest.mock import Mock
from clientfactory.utils.requests.base import RequestUtilConfig
from clientfactory.utils.requests.iterator import (
    Iterator, ParamIterator, IteratorConfig, IteratorStrategy
)

@pytest.fixture
def mock_resource():
    return Mock(return_value={"data": "test"})

def test_param_iterator_init():
    """Test ParamIterator initialization"""
    # Valid initializations
    p1 = ParamIterator("test", start=1, end=3)
    assert p1.name == "test"
    assert list(p1.generate()) == [1, 2, 3]

    p2 = ParamIterator("test", values=[1, 2, 3])
    assert list(p2.generate()) == [1, 2, 3]

    # Should convert iterables to list
    p3 = ParamIterator("test", values=range(3))
    assert isinstance(p3.values, list)
    assert p3.values == [0, 1, 2]

    # Should raise with invalid config
    with pytest.raises(ValueError):
        ParamIterator("test")  # No values or start/end

def test_iterator_product_strategy(mock_resource):
    """Test product iteration strategy"""
    iterator = Iterator(
        mock_resource,
        params={
            "brand": {"values": ["Nike", "Adidas"]},
            "category": {"values": ["shoes", "shirts"]}
        },
        strategy="product"
    )

    results = list(iterator.iterate())
    expected_params = [
        {"brand": "Nike", "category": "shoes"},
        {"brand": "Nike", "category": "shirts"},
        {"brand": "Adidas", "category": "shoes"},
        {"brand": "Adidas", "category": "shirts"}
    ]

    assert len(results) == 4
    assert [params for params, _ in results] == expected_params
    assert mock_resource.call_count == 4

def test_iterator_zip_strategy(mock_resource):
    """Test zip iteration strategy"""
    iterator = Iterator(
        mock_resource,
        params={
            "page": {"start": 1, "end": 3},
            "size": {"values": [10, 20, 30]}
        },
        strategy="zip"
    )

    results = list(iterator.iterate())
    expected_params = [
        {"page": 1, "size": 10},
        {"page": 2, "size": 20},
        {"page": 3, "size": 30}
    ]

    assert len(results) == 3
    assert [params for params, _ in results] == expected_params
    assert mock_resource.call_count == 3

def test_iterator_chain_strategy(mock_resource):
    """Test chain iteration strategy"""
    iterator = Iterator(
        mock_resource,
        params={
            "brand": {"values": ["Nike", "Adidas"]},
            "category": {"values": ["shoes"]}
        },
        strategy="chain"
    )

    results = list(iterator.iterate())
    expected_params = [
        {"brand": "Nike"},
        {"brand": "Adidas"},
        {"category": "shoes"}
    ]

    assert len(results) == 3
    assert [params for params, _ in results] == expected_params
    assert mock_resource.call_count == 3

def test_iterator_runtime_param_update(mock_resource):
    """Test updating parameter values during iteration"""
    iterator = Iterator(
        mock_resource,
        params={
            "brand": {"values": ["Nike"]}
        }
    )

    # Update values during iterate call
    results = list(iterator.iterate(brand=["Adidas", "Puma"]))
    expected_params = [
        {"brand": "Adidas"},
        {"brand": "Puma"}
    ]

    assert [params for params, _ in results] == expected_params

def test_iterator_error_handling(mock_resource):
    """Test error handling during iteration"""
    mock_resource.side_effect = Exception("Test error")

    # Should not raise by default
    iterator = Iterator(
        mock_resource,
        params={"test": {"values": [1, 2]}}
    )
    results = list(iterator.iterate())
    assert len(results) == 0

    # Should raise with raiseonerror=True
    iterator.config.raiseonerror = True
    with pytest.raises(Exception):
        list(iterator.iterate())

def test_iterator_delay(mock_resource):
    """Test delay between iterations"""
    iterator = Iterator(
        mock_resource,
        params={"test": {"values": [1, 2]}},
        config=RequestUtilConfig(delay=0.1)
    )

    import time
    start = time.time()
    list(iterator.iterate())
    duration = time.time() - start

    assert duration >= 0.1  # At least one delay between two iterations

@pytest.mark.parametrize("strategy", [
    IteratorStrategy.PRODUCT,
    "product",
    IteratorStrategy.ZIP,
    "zip",
    IteratorStrategy.CHAIN,
    "chain"
])
def test_iterator_strategy_types(strategy, mock_resource):
    """Test different ways of specifying strategy"""
    iterator = Iterator(
        mock_resource,
        params={"test": {"values": [1]}},
        strategy=strategy
    )
    assert isinstance(iterator.config.strategy, IteratorStrategy)

def test_invalid_strategy():
    """Test invalid strategy handling"""
    with pytest.raises(ValueError):
        Iterator(
            Mock(),
            params={"test": {"values": [1]}},
            strategy="invalid"
        )
