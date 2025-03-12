# ~/ClientFactory/src/clientfactory/utils/tests/test_response_itemize.py
# ~/ClientFactory/src/clientfactory/utils/tests/test_response_itemize.py

import pytest
from clientfactory.utils.response import Response, ResponseMap, ObjectMap

@pytest.fixture
def mock_request():
    class MockRequest:
        url = "https://api.example.com/test"
    return MockRequest()

@pytest.fixture
def simple_list_response(mock_request):
    """Response with simple list of items"""
    return Response(
        status_code=200,
        headers={},
        raw_content=b'''[
            {"name": "item1", "amount": 100, "brand": "nike"},
            {"name": "item2", "amount": 200, "brand": "adidas"}
        ]''',
        request=mock_request
    )

@pytest.fixture
def nested_response(mock_request):
    """Response with nested items structure"""
    return Response(
        status_code=200,
        headers={},
        raw_content=b'''{
            "items": [
                {"name": "item1", "price": {"usd": 100}, "details": {"brand": "nike"}},
                {"name": "item2", "price": {"usd": 200}, "details": {"brand": "adidas"}}
            ]
        }''',
        request=mock_request
    )

@pytest.fixture
def single_response(mock_request):
    """Response with single item"""
    return Response(
        status_code=200,
        headers={},
        raw_content=b'''
            {"name": "item1", "amount": 100, "brand": "nike"}
        ''',
        request=mock_request
    )

def test_basic_mapping(simple_list_response):
    """Test basic field mapping"""
    ItemMap = ObjectMap(
        title="name",
        price="amount",
        brand="brand"
    )

    items = simple_list_response.itemize(ResponseMap(objectmap=ItemMap))
    assert len(items) == 2
    assert items[0].title == "item1"
    assert items[0].price == 100
    assert items[0].brand == "nike"
    assert items[1].title == "item2"
    assert items[1].price == 200
    assert items[1].brand == "adidas"

def test_nested_path_mapping(nested_response):
    """Test mapping with nested paths"""
    ItemMap = ObjectMap(
        title="name",
        price="price.usd",
        brand="details.brand"
    )

    items = nested_response.itemize(ResponseMap(
        objectmap=ItemMap,
        objectspath="items"
    ))
    assert len(items) == 2
    assert items[0].title == "item1"
    assert items[0].price == 100
    assert items[0].brand == "nike"

def test_single_item_mapping(single_response):
    """Test mapping single item response"""
    ItemMap = ObjectMap(
        title="name",
        price="amount"
    )

    items = single_response.itemize(ResponseMap(objectmap=ItemMap))
    assert len(items) == 1
    assert items[0].title == "item1"
    assert items[0].price == 100

def test_transform_mapping(nested_response):
    """Test mapping with transform function"""
    def uppercase_transform(data):
        items = data['items']
        return [{
            'name': item['name'].upper(),
            'amount': item['price']['usd']
        } for item in items]

    ItemMap = ObjectMap(
        title="name",
        price="amount"
    )

    items = nested_response.itemize(ResponseMap(
        objectmap=ItemMap,
        transform=uppercase_transform
    ))
    assert len(items) == 2
    assert items[0].title == "ITEM1"
    assert items[0].price == 100

def test_missing_fields(simple_list_response):
    """Test handling of missing fields"""
    ItemMap = ObjectMap(
        title="name",
        price="amount",
        missing="nonexistent"
    )

    items = simple_list_response.itemize(ResponseMap(objectmap=ItemMap))
    assert len(items) == 2
    assert items[0].title == "item1"
    assert items[0].price == 100
    assert items[0].missing is None

def test_callable_mapping(simple_list_response):
    def test_callable_mapping(simple_list_response):
        """Test mapping with callable"""
        ItemMap = ObjectMap(
            title="name",
            price=lambda x: float(x['amount']) * 1.1  # 10% markup
        )

        items = simple_list_response.itemize(ResponseMap(objectmap=ItemMap))
        assert len(items) == 2
        assert items[0].title == "item1"
        assert items[0].price == pytest.approx(110.0)

def test_error_response(mock_request):
    """Test handling of error response"""
    error_response = Response(
        status_code=404,
        headers={},
        raw_content=b'{"error": "Not found"}',
        request=mock_request
    )

    ItemMap = ObjectMap(title="name")
    items = error_response.itemize(ResponseMap(objectmap=ItemMap))
    assert len(items) == 0

def test_invalid_json(mock_request):
    """Test handling of invalid JSON"""
    bad_response = Response(
        status_code=200,
        headers={},
        raw_content=b'{"bad json",}',
        request=mock_request
    )

    ItemMap = ObjectMap(title="name")
    items = bad_response.itemize(ResponseMap(objectmap=ItemMap))
    assert len(items) == 0
