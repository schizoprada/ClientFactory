# ~/ClientFactory/tests/test_utils_requests_chain.py
import pytest
from unittest.mock import Mock
from clientfactory.utils.requests.base import RequestUtilConfig
from clientfactory.utils.requests.chain import RequestChain, ChainConfig, ChainLink

@pytest.fixture
def mock_search():
    return Mock(return_value={"data": "test", "categories": ["shoes", "shirts"]})

def test_chain_initialization():
    """Test chain initialization and configuration"""
    chain = RequestChain()
    assert len(chain.links) == 0
    assert isinstance(chain.config, ChainConfig)

def test_chain_add_methods():
    """Test different methods of adding links"""
    mock = Mock()

    # Method chaining
    chain1 = RequestChain()
    chain1.add(mock, {"a": 1}).add(mock, {"b": 2})
    assert len(chain1.links) == 2

    # Operator syntax
    chain2 = RequestChain()
    chain2 @ (mock, {"a": 1}) @ (mock, {"b": 2})
    assert len(chain2.links) == 2

    # Mixed syntax
    chain3 = (
        RequestChain()
        .add(mock, {"a": 1})
        @ (mock, {"b": 2})
    )
    assert len(chain3.links) == 2

def test_chain_execution_basic(mock_search):
    """Test basic chain execution"""
    chain = (
        RequestChain()
        @ (mock_search, {"query": "nike"})
        @ (mock_search, {"brand": "nike"})
    )

    results = chain()  # Test __call__
    assert len(results) == 2
    assert all(isinstance(r[1], dict) for r in results)
    assert mock_search.call_count == 2

def test_chain_data_extraction():
    """Test extracting specific keys from responses"""
    mock = Mock(return_value={"categories": ["shoes"], "extra": "data"})

    chain = RequestChain()
    chain.add(
        mock,
        {"query": "nike"},
        ChainConfig(xkey="categories")
    )

    results = chain()
    assert results[0][1] == ["shoes"]  # Only categories extracted

def test_chain_param_transformation():
    """Test parameter transformation between requests"""
    mock1 = Mock(return_value={"categories": ["shoes"]})
    mock2 = Mock(return_value={"items": []})

    chain = RequestChain()
    chain.add(
        mock1,
        {"query": "nike"},
        ChainConfig(xkey="categories")
    ).add(
        mock2,
        lambda prev: {"category": prev[0]}  # Use first category
    )

    results = chain()
    assert results[1][0] == {"category": "shoes"}

def test_chain_error_handling():
    """Test error handling in chain"""
    mock1 = Mock(return_value={"data": "test"})
    mock2 = Mock(side_effect=ValueError("test error"))
    mock3 = Mock(return_value={"data": "final"})

    # Test stoponfail=True
    chain1 = RequestChain(config=ChainConfig(stoponfail=True))
    chain1.add(mock1, {}).add(mock2, {}).add(mock3, {})

    with pytest.raises(ValueError):
        chain1()

    # Test stoponfail=False
    chain2 = RequestChain(config=ChainConfig(stoponfail=False))
    chain2.add(mock1, {}).add(mock2, {}).add(mock3, {})

    results = chain2()
    assert len(results) == 3
    assert isinstance(results[1][1], ValueError)
    assert results[2][1]["data"] == "final"

def test_chain_context_manager():
    """Test using chain as context manager"""
    mock = Mock(return_value={"data": "test"})

    with RequestChain() as chain:
        chain.add(mock, {"test": 1})
        results = chain()

    assert len(results) == 1
    assert mock.called

def test_chain_complex_transformation():
    """Test complex data transformation between requests"""
    mock1 = Mock(return_value={"items": [
        {"id": 1, "category": "shoes"},
        {"id": 2, "category": "shirts"}
    ]})
    mock2 = Mock(return_value={"data": "test"})

    def transform(prev):
        return {
            "ids": [item["id"] for item in prev["items"]],
            "categories": list(set(item["category"] for item in prev["items"]))
        }

    chain = RequestChain()
    chain.add(mock1, {}).add(mock2, transform)

    results = chain()
    assert results[1][0]["ids"] == [1, 2]
    assert set(results[1][0]["categories"]) == {"shoes", "shirts"}  # Compare as sets instead

def test_chain_config_inheritance():
    """Test config inheritance and overriding"""
    mock = Mock(return_value={"data": "test", "key": "value"})

    # Default config
    chain = RequestChain(config=ChainConfig(xkey="data"))
    chain.add(mock, {})  # Should inherit xkey="data"
    results = chain()
    assert results[0][1] == "test"

    # Override config
    chain.add(mock, {}, ChainConfig(xkey="key"))
    results = chain()
    assert results[1][1] == "value"
