# ~/ClientFactory/tests/test_utils_response_itemize.py
import pytest
from clientfactory.utils.response import Response, ResponseMap, ObjectMap

class TestItem(ObjectMap):
    """Test item mapping"""
    id: str = 'id'  # maps directly to response field
    name: str = 'name'
    price: float = 'price'

@pytest.fixture
def mock_list_response():
    """Response with list of items"""
    return Response(
        status_code=200,
        headers={},
        raw_content=b'''[
            {"id": "1", "name": "test1", "price": 100},
            {"id": "2", "name": "test2", "price": 200}
        ]''',
        request=None
    )

@pytest.fixture
def mock_nested_response():
    """Response with nested items"""
    return Response(
        status_code=200,
        headers={},
        raw_content=b'''{
            "items": [
                {"id": "1", "name": "test1", "price": 100},
                {"id": "2", "name": "test2", "price": 200}
            ]
        }''',
        request=None
    )

@pytest.fixture
def mock_single_response():
    """Response with single item"""
    return Response(
        status_code=200,
        headers={},
        raw_content=b'''
            {"id": "1", "name": "test1", "price": 100}
        ''',
        request=None
    )

def test_direct_list_mapping(mock_list_response):
    """Test mapping direct list response"""
    mapping = ResponseMap(objectmap=TestItem)
    items = mock_list_response.itemize(mapping)
    assert len(items) == 2
    assert items[0].id == "1"
    assert items[0].name == "test1"
    assert items[0].price == 100

def test_nested_mapping(mock_nested_response):
    """Test mapping nested response"""
    mapping = ResponseMap(
        objectmap=TestItem,
        objectspath="items"
    )
    items = mock_nested_response.itemize(mapping)
    assert len(items) == 2
    assert items[0].id == "1"
    assert items[1].name == "test2"

def test_single_object_mapping(mock_single_response):
    """Test mapping single object response"""
    mapping = ResponseMap(objectmap=TestItem)
    items = mock_single_response.itemize(mapping)
    assert len(items) == 1
    assert items[0].id == "1"

class NestedTestItem(ObjectMap):
    """Test item with nested field mapping"""
    id: str = 'id'
    name: str = 'data.name'
    price: float = 'data.info.price'

def test_nested_field_mapping(mock_nested_response):
    """Test mapping nested fields"""
    mock_nested_response.raw_content = b'''{
        "items": [
            {"id": "1", "data": {"name": "test1", "info": {"price": 100}}},
            {"id": "2", "data": {"name": "test2", "info": {"price": 200}}}
        ]
    }'''

    mapping = ResponseMap(
        objectmap=NestedTestItem,
        objectspath="items"
    )
    items = mock_nested_response.itemize(mapping)
    assert len(items) == 2
    assert items[0].name == "test1"
    assert items[0].price == 100

class TransformTestItem(ObjectMap):
    """Test item with transform"""
    id: str = 'id'
    name: str = 'name'  # will be uppercase from transform
    price: float = 'price'

def test_transform_mapping(mock_nested_response):
    """Test mapping with transform function"""
    def custom_transform(data):
        return [{
            'id': i['id'],
            'name': i['name'].upper(),
            'price': i['price']
        } for i in data['items']]

    mapping = ResponseMap(
        objectmap=TransformTestItem,
        transform=custom_transform
    )
    items = mock_nested_response.itemize(mapping)
    assert len(items) == 2
    assert items[0].name == "TEST1"
