# ~/ClientFactory/src/clientfactory/clients/managed/tests/test_resources.py
import pytest
from clientfactory import Client
from clientfactory.utils.request import RequestMethod
from clientfactory.clients.managed import (
    managedresource, managedop,
    Operations, C, R, U, D
)

# Test Resource Definition
@managedresource
class TestResource:
    path = "test"
    operations = Operations(
        C(RequestMethod.POST),
        R(RequestMethod.GET),
        U(RequestMethod.PUT),
        D(RequestMethod.DELETE)
    )

    @managedop(RequestMethod.POST)
    def custom(self, **kwargs):
        """Custom operation"""
        pass

# Test Client
class TestClient(Client):
    baseurl = "https://api.test.com"
    test = TestResource

def test_resource_initialization():
    """Test managed resource initialization"""
    client = TestClient()
    assert hasattr(client, 'test')
    assert 'create' in client.test._config.methods
    assert 'read' in client.test._config.methods
    assert 'update' in client.test._config.methods
    assert 'delete' in client.test._config.methods
    assert 'custom' in client.test._config.methods

def test_operation_methods():
    """Test operation method generation"""
    client = TestClient()
    assert hasattr(client.test, 'create')
    assert hasattr(client.test, 'read')
    assert hasattr(client.test, 'update')
    assert hasattr(client.test, 'delete')
    assert hasattr(client.test, 'custom')

def test_operation_request_building(mocker):
    """Test request building for operations"""
    client = TestClient()

    # Mock session send
    mock_send = mocker.patch('clientfactory.session.base.BaseSession.send')
    mock_send.return_value = mocker.Mock(status_code=200)

    # Test create operation
    client.test.create(data={"test": "value"})
    create_call = mock_send.call_args_list[0]
    assert create_call[0][0].method == RequestMethod.POST
    assert create_call[0][0].url == "https://api.test.com/test"

    # Test read operation
    client.test.read(id=123)
    read_call = mock_send.call_args_list[1]
    assert read_call[0][0].method == RequestMethod.GET
    assert read_call[0][0].url == "https://api.test.com/test"

def test_custom_operation_handling(mocker):
    """Test custom operation handling"""
    client = TestClient()

    # Mock session send
    mock_send = mocker.patch('clientfactory.session.base.BaseSession.send')
    mock_send.return_value = mocker.Mock(status_code=200)

    # Test custom operation
    client.test.custom(data={"custom": "value"})
    custom_call = mock_send.call_args_list[0]
    assert custom_call[0][0].method == RequestMethod.POST
    assert custom_call[0][0].url == "https://api.test.com/test"

def test_operation_preprocessing(mocker):
    """Test operation preprocessor execution"""
    @managedresource
    class PreprocessResource:
        path = "preprocess"

        def preprocess_request(self, request):
            request.headers['Custom'] = 'Value'
            return request

        operations = Operations(
            C(RequestMethod.POST, preprocess=preprocess_request)
        )

    class PreprocessClient(Client):
        baseurl = "https://api.test.com"
        preprocess = PreprocessResource

    client = PreprocessClient()

    # Mock session send
    mock_send = mocker.patch('clientfactory.session.base.BaseSession.send')
    mock_send.return_value = mocker.Mock(status_code=200)

    client.preprocess.create()
    assert mock_send.call_args[0][0].headers.get('Custom') == 'Value'

def test_operation_postprocessing(mocker):
    """Test operation postprocessor execution"""
    @managedresource
    class PostprocessResource:
        path = "postprocess"

        def postprocess_response(self, response):
            return {'processed': True}

        operations = Operations(
            R(RequestMethod.GET, postprocess=postprocess_response)
        )

    class PostprocessClient(Client):
        baseurl = "https://api.test.com"
        postprocess = PostprocessResource

    client = PostprocessClient()

    # Mock session send
    mock_send = mocker.patch('clientfactory.session.base.BaseSession.send')
    mock_send.return_value = mocker.Mock(status_code=200)

    result = client.postprocess.read()
    assert result == {'processed': True}
