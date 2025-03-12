# ~/ClientFactory/tests/test_utils_requests_batch.py
import pytest
from unittest.mock import Mock
import time
from clientfactory.utils.requests.base import RequestUtilConfig
from clientfactory.utils.requests.batch import BatchProcessor, BatchConfig

@pytest.fixture
def mock_resource():
    return Mock(return_value={"data": "test"})

def test_batch_processor_init():
    """Test BatchProcessor initialization"""
    # Valid init
    processor = BatchProcessor(
        Mock(),
        params={"test": [1, 2, 3]}
    )
    assert processor.config.size == 10  # Default batch size

    # Unequal lengths should raise
    with pytest.raises(ValueError, match="equal in length"):
        BatchProcessor(
            Mock(),
            params={
                "a": [1, 2, 3],
                "b": [1, 2]
            }
        )

def test_batch_processing_basic(mock_resource):
    """Test basic batch processing"""
    processor = BatchProcessor(
        mock_resource,
        params={
            "param1": list(range(5)),
            "param2": list('abcde')
        },
        config=BatchConfig(size=2)
    )

    successes, failures = processor.process()
    assert len(successes) == 5
    assert len(failures) == 0
    assert mock_resource.call_count == 5

def test_batch_processing_with_failure():
    """Test batch processing with failures"""
    def mock_func(**kwargs):
        if kwargs["param1"] == 2:
            raise ValueError("test error")
        return {"data": "test"}

    processor = BatchProcessor(
        mock_func,
        params={"param1": list(range(5))},
        config=BatchConfig(size=2, collectfailed=True)
    )

    successes, failures = processor.process()
    assert len(successes) == 4  # Should succeed for 0,1,3,4
    assert len(failures) == 1   # Should fail for 2
    assert failures[0][0]["param1"] == 2  # The failed value
    assert isinstance(failures[0][1], ValueError)  # The error

def test_batch_processing_stop_on_fail():
    """Test stopping on first failure"""
    def mock_func(**kwargs):
        if kwargs["param1"] == 2:
            raise ValueError("test error")
        return {"data": "test"}

    processor = BatchProcessor(
        mock_func,
        params={"param1": list(range(5))},
        config=BatchConfig(size=2, stoponfail=True)
    )

    with pytest.raises(ValueError, match="test error"):
        processor.process()

def test_batch_delay():
    """Test delay between batches"""
    processor = BatchProcessor(
        Mock(),
        params={"test": list(range(5))},
        config=BatchConfig(size=2, delay=0.1)
    )

    start = time.time()
    processor.process()
    duration = time.time() - start

    # Should have 2 delays (3 batches - 1)
    assert duration >= 0.2

def test_batch_context_manager(mock_resource):
    """Test context manager interface"""
    with BatchProcessor(
        mock_resource,
        params={"test": list(range(3))}
    ) as processor:
        successes, failures = processor.process()
        assert len(successes) == 3
        assert len(failures) == 0

def test_batch_parameter_combinations():
    """Test processing multiple parameter combinations"""
    results = {}
    def mock_func(**kwargs):
        key = tuple(kwargs.values())
        results[key] = kwargs
        return kwargs

    processor = BatchProcessor(
        mock_func,
        params={
            "a": [1, 2],
            "b": ["x", "y"]
        },
        config=BatchConfig(size=1)
    )

    successes, failures = processor.process()
    assert len(successes) == 2
    assert (1, "x") in results
    assert (2, "y") in results

def test_empty_params():
    """Test handling of empty parameter lists"""
    processor = BatchProcessor(
        Mock(),
        params={"test": []}
    )

    successes, failures = processor.process()
    assert len(successes) == 0
    assert len(failures) == 0

def test_single_item_batch():
    """Test processing single-item batch"""
    mock = Mock()
    processor = BatchProcessor(
        mock,
        params={"test": [1]},
        config=BatchConfig(size=5)  # Batch size larger than items
    )

    processor.process()
    assert mock.call_count == 1

def test_large_batch_handling():
    """Test handling of large batches"""
    items = list(range(25))
    calls = []

    def mock_func(**kwargs):
        calls.append(kwargs)
        return kwargs

    processor = BatchProcessor(
        mock_func,
        params={"test": items},
        config=BatchConfig(size=10)
    )

    successes, failures = processor.process()
    assert len(successes) == 25
    assert len(calls) == 25
    # Should have processed in 3 batches
    assert len(set(id(batch) for batch in calls)) >= 3
