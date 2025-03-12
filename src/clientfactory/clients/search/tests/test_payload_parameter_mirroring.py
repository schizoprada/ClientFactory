# ~/ClientFactory/src/clientfactory/clients/search/tests/test_payload_parameter_mirroring.py
import pytest
from clientfactory.clients.search.core import Parameter, Payload, Protocol, ProtocolType
from clientfactory.utils.request import RequestMethod
from clientfactory.clients.search.transformers import PayloadTransform
from clientfactory.transformers.base import MergeMode

def test_mercari_style_mirroring():
    """Test that reproduces the Mercari API payload structure and mirroring requirements"""

    payload = Payload(
        page=Parameter(
            name="pageToken",
            process=lambda x: f"v1:{x-1}" if (x is not None) and (x > 0) else "",
            mirrorto=[],  # Mirror to all instances of pageToken
            default=1
        ),
        hits=Parameter(
            name="pageSize",
            default=120,
            mirrorto=[]  # Mirror to all instances of pageSize
        ),
        sort=Parameter(default="SORT_SCORE"),
        order=Parameter(default="ORDER_DESC"),
        brand=Parameter(name="brandId", type=list, default=[]),
    )

    # Define transforms
    base_values = {
        "pageToken": None,
        "pageSize": None,
        "sort": None,
        "order": None,
        "brandId": None
    }

    transforms = [
        PayloadTransform(
            key="searchCondition",  # This transform keeps values at root AND puts them in searchCondition
            valmap={
                **base_values,  # Root level values
                "searchCondition": base_values.copy()  # Same structure under searchCondition
            },
            order=0,
            mergemode=MergeMode.UPDATE
        )
    ]

    test_cases = [
        ({"page": 1}, ["pageToken", "searchCondition.pageToken"]),
        ({"page": 2}, ["pageToken", "searchCondition.pageToken"]),
        ({"page": 3}, ["pageToken", "searchCondition.pageToken"]),
    ]

    for params, expected_paths in test_cases:
        # First map parameters
        result = payload.map(**params)

        # Then apply transform
        for transform in transforms:
            result = transform.apply(result, {})

        # Get actual paths where pageToken exists
        actual_paths = payload._findallpaths(result, "pageToken")

        # Verify paths exist
        assert set(actual_paths) == set(expected_paths), \
            f"PageToken not mirrored correctly for page={params['page']}"

        # Verify values match at all paths
        expected_value = f"v1:{params['page']-1}" if params['page'] > 0 else ""
        for path in expected_paths:
            current = result
            if "." in path:
                parts = path.split(".")
                for part in parts[:-1]:
                    current = current[part]
                final_part = parts[-1]
            else:
                final_part = path
            assert current[final_part] == expected_value, \
                f"Incorrect value at {path} for page={params['page']}"


def test_parameter_mirroring_with_transforms():
    """Test that mirroring works correctly with transforms"""
    payload = Payload(
        test_param=Parameter(
            name="test",
            default="default_value",
            mirrorto=["nested.test"]
        )
    )

    transform = PayloadTransform(
        key="",  # Empty key = operate at root level
        valmap={
            "test": None,  # Keep root level value
            "nested": {
                "test": None,
                "other": "value"
            }
        },
        nestkey=False,  # Don't nest everything under a key
        mergemode=MergeMode.UPDATE  # Merge, don't replace
    )

    # First map parameters
    result = payload.map(test_param="test_value")

    # Then apply transform
    result = transform.apply(result, {})

    # Verify values
    assert result["test"] == "test_value"  # Root level preserved
    assert "nested" in result
    assert result["nested"]["test"] == "test_value"  # Nested value mirrored
    assert result["nested"]["other"] == "value"  # Transform value preserved

def test_findallpaths_logging():
    """Test the path finding functionality with detailed logging"""
    payload = Payload()

    test_data = {
        "key1": "value1",
        "nested": {
            "key1": "value2",
            "deeper": {
                "key1": "value3"
            }
        },
        "searchCondition": {
            "key1": "value4"
        }
    }

    paths = payload._findallpaths(test_data, "key1")

    expected_paths = [
        "key1",
        "nested.key1",
        "nested.deeper.key1",
        "searchCondition.key1"
    ]

    assert set(paths) == set(expected_paths)

def test_empty_mirrorto_list():
    """Test behavior when mirrorto is an empty list (mirror everywhere)"""
    payload = Payload(
        param=Parameter(
            name="test",
            mirrorto=[]  # Should mirror everywhere
        )
    )

    test_data = {
        "test": "value",
        "nested": {
            "other": "data"
        }
    }

    mapped = payload.map(param="mirror_me")
    paths = payload._findallpaths(mapped, "test")

    assert len(paths) > 0, "No paths found for mirroring"
    assert all(mapped.get(p) == "mirror_me" for p in paths), \
        "Not all instances were mirrored correctly"
