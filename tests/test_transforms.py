# ~/ClientFactory/tests/test_transforms.py
import pytest
from clientfactory.transformers.base import (
    Transform,
    Transformer,
    TransformType,
    TransformOperation,
    TransformPipeline
)
from clientfactory.client import Client
from clientfactory.resources.decorators import resource, get
from clientfactory.clients.search.transformers import (
    PayloadTransform,
    URLTransform
)

# Basic Transform Tests
def test_basic_transform():
    class SimpleTransform(Transform):
        def __init__(self):
            super().__init__(
                type=TransformType.PAYLOAD,
                operation=TransformOperation.MAP,
                target="test"
            )

        def apply(self, value):
            return {k: v.upper() if isinstance(v, str) else v
                   for k, v in value.items()}

    transform = SimpleTransform()
    result = transform({"name": "test", "value": 123})
    assert result == {"name": "TEST", "value": 123}

# Transform Pipeline Tests
def test_transform_pipeline():
    class AddKeyTransform(Transform):
        def __init__(self, key, value):
            super().__init__(
                type=TransformType.PAYLOAD,
                operation=TransformOperation.MERGE,
                target="add"
            )
            self.key = key
            self.value = value

        def apply(self, value):
            if not isinstance(value, dict):
                value = {}
            value[self.key] = self.value
            return value

    pipeline = TransformPipeline([
        AddKeyTransform("first", 1),
        AddKeyTransform("second", 2)
    ])

    result = pipeline({})
    assert result == {"first": 1, "second": 2}

# Client Integration Tests
def test_payload_transform():
    transform = PayloadTransform("defaults", {"sort": "desc", "limit": 10})
    result = transform({"query": "test"})

    assert isinstance(result, dict)
    assert result["sort"] == "desc"
    assert result["limit"] == 10
    assert result["query"] == "test"

def test_url_transform():
    transform = URLTransform("search", "https://api.test.com/search")
    result = transform({"sort": "desc", "limit": "10", "query": "test"})

    assert isinstance(result, str)
    assert result == "https://api.test.com/search?sort=desc&limit=10&query=test"

def test_client_transforms():
    class TestClient(Client):
        baseurl = "https://api.test.com"

        @resource
        class Search:
            # Only use PayloadTransform for this test
            transforms = [
                PayloadTransform("defaults", {"sort": "desc", "limit": 10})
            ]

            @get("/search")
            def execute(self, **kwargs):
                return kwargs

    client = TestClient()
    result = client.search.transform({"query": "test"})

    assert isinstance(result, dict)
    assert result["sort"] == "desc"
    assert result["limit"] == 10
    assert result["query"] == "test"

def test_client_transform_pipeline():
    """Test complete transform pipeline including URL transformation"""
    class TestClient(Client):
        baseurl = "https://api.test.com"

        @resource
        class Search:
            transforms = [
                PayloadTransform("defaults", {"sort": "desc", "limit": 10}),
                URLTransform("search", "https://api.test.com/search")
            ]

            @get("/search")
            def execute(self, **kwargs):
                return kwargs

    client = TestClient()
    result = client.search.transform({"query": "test"})

    assert isinstance(result, str)
    assert "sort=desc" in result
    assert "limit=10" in result
    assert "query=test" in result
    assert result.startswith("https://api.test.com/search")

# Transform Composition Tests
def test_transform_composition():
    class UpperTransform(Transform):
        def __init__(self):
            super().__init__(
                type=TransformType.PAYLOAD,
                operation=TransformOperation.MAP,
                target="upper"
            )

        def apply(self, value):
            return {k: v.upper() if isinstance(v, str) else v
                   for k, v in value.items()}

    class AddPrefixTransform(Transform):
        def __init__(self, prefix):
            super().__init__(
                type=TransformType.PAYLOAD,
                operation=TransformOperation.MAP,
                target="prefix"
            )
            self.prefix = prefix

        def apply(self, value):
            return {k: f"{self.prefix}_{v}" if isinstance(v, str) else v
                   for k, v in value.items()}

    # Test composition using >>
    transform = UpperTransform() >> AddPrefixTransform("test")
    result = transform({"name": "value", "num": 123})

    assert result["name"] == "test_VALUE"
    assert result["num"] == 123

# Order Tests
def test_transform_order():
    executed = []

    class OrderedTransform(Transform):
        def __init__(self, name: str, order: int):
            super().__init__(
                type=TransformType.PAYLOAD,
                operation=TransformOperation.MAP,
                target="order",
                order=order
            )
            self.name = name

        def apply(self, value):
            executed.append(self.name)
            return value

    pipeline = TransformPipeline([
        OrderedTransform("third", 3),
        OrderedTransform("first", 1),
        OrderedTransform("second", 2)
    ])

    pipeline({})
    assert executed == ["first", "second", "third"]

# Error Handling Tests
def test_transform_errors():
    class ErrorTransform(Transform):
        def __init__(self):
            super().__init__(
                type=TransformType.PAYLOAD,
                operation=TransformOperation.MAP,
                target="error"
            )

        def apply(self, value):
            raise ValueError("Test error")

    with pytest.raises(ValueError):
        ErrorTransform()({})
