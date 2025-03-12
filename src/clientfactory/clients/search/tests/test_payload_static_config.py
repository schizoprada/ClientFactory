# ~/ClientFactory/src/clientfactory/clients/search/tests/test_payload_static_config.py
import pytest
from clientfactory.clients.search.core import Parameter, NestedParameter, Payload

def test_static_config_basic():
    payload = Payload(
        parameters={
            "query": Parameter(name="q"),
            "page": Parameter(name="p", default=1)
        },
        static={
            "market": "US",
            "language": "en"
        }
    )

    mapped = payload.map(query="shoes")
    assert mapped["market"] == "US"
    assert mapped["language"] == "en"
    assert mapped["q"] == "shoes"
    assert mapped["p"] == 1

def test_static_config_override():
    # Static config shouldn't be overrideable by dynamic parameters
    payload = Payload(
        query=Parameter(name="q"),
        static={"q": "static_value"}
    )

    mapped = payload.map(query="dynamic_value")
    assert mapped["q"] == "dynamic_value"  # Dynamic parameters take precedence

def test_static_config_nested():
    payload = Payload(
        filters=NestedParameter(
            name="filters",
            children={
                "price": NestedParameter(
                    name="price",
                    children={
                        "min": Parameter(name="price.gte"),
                        "max": Parameter(name="price.lte")
                    }
                )
            }
        ),
        static={
            "market": "US",  # Simple static value
            "constant": "value"
        }
    )

    mapped = payload.map(filters={"price": {"min": 10, "max": 100}})
    assert mapped["constant"] == "value"  # Static values present
    assert mapped["market"] == "US"
    assert mapped["price.gte"] == 10  # Nested parameter properly mapped
    assert mapped["price.lte"] == 100
