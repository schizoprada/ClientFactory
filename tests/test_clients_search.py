import pytest
from clientfactory import (
    Search,
    SearchClient,
    SearchResource,
    SearchResourceConfig,
    Parameter,
    Payload,
    Protocol,
    ProtocolType,
    searchresource,
    Client,
    RequestMethod,
    Response
)


class SimpleSearchClient(SearchClient):
    baseurl = "https://api.test.com"
    protocol = Protocol(
        ProtocolType.REST,
        RequestMethod.GET
    )
    payload = Payload(
        query=Parameter(name="query"),  # Will default to "query"
        hits=Parameter(default=20)    # Will default to "hits"
    )
    oncall = True

class ResourceSearchClient(Client):
    baseurl = "https://api.test.com"

    @searchresource
    class Search:
        protocol = Protocol(
            ProtocolType.REST,
            RequestMethod.GET
        )
        payload = Payload(
            query=Parameter(),  # Will default to "query"
            hits=Parameter()    # Will default to "hits"
        )
        oncall = True



# Mock Response Factory
def create_mock_response(status_code=200, json_data=None, request=None):
    """Create a mock Response object"""
    return Response(
        status_code=status_code,
        headers={},
        raw_content=str(json_data).encode() if json_data else b"",
        request=request
    )

# Mock Session Send
def mock_session_send(request):
    """Mock session.send() method"""
    if request.method == RequestMethod.GET:
        # Preserve the formatted params in the response
        return create_mock_response(
            json_data={"results": [], "params": request.params},
            request=request
        )
    elif request.method == RequestMethod.POST:
        if "algolia" in request.url:
            # Properly structure Algolia response
            params = request.json["requests"][0]["params"]
            return create_mock_response(
                json_data={
                    "results": [{
                        "hits": [],
                        "nbHits": 0,
                        "page": 0,
                        "nbPages": 0,
                        "hitsPerPage": params.get("hitsPerPage", 20),
                        "query": params.get("query", "")
                    }]
                },
                request=request
            )
        return create_mock_response(
            json_data={"results": [], "params": request.json},
            request=request
        )

@pytest.fixture(autouse=True)
def mock_session(monkeypatch):
    """Automatically mock session for all tests"""
    def mock_send(self, request):
        return mock_session_send(request)

    monkeypatch.setattr("clientfactory.session.base.BaseSession.send", mock_send)

## TESTS ##

def test_parameter_flow():
    client = SimpleSearchClient()

    # Original params
    test_params = {"query": "test", "hits": 10}

    # Check Payload mapping
    mapped_params = client.payload.map(**test_params)
    print(f"\nPayload map: {test_params} -> {mapped_params}")

    # Check Adapter formatting
    formatted_params = client.adapter.formatparams(mapped_params)
    print(f"Adapter format: {mapped_params} -> {formatted_params}")

    # Full execution for comparison
    response = client._execute(**test_params)
    print(f"Final params in request: {response.request.params}")


def test_base_search_functionality():
    """Test that Search base class functionality works in both Client and Resource contexts"""
    # Test in Client context
    client = SimpleSearchClient()
    assert isinstance(client, Search)
    assert isinstance(client, Client)

    # Test in Resource context
    resource_client = ResourceSearchClient()
    assert isinstance(resource_client.search, SearchResource)
    assert isinstance(resource_client.search, Search)

def test_search_client_initialization():
    client = SimpleSearchClient()
    assert client.protocol.type == ProtocolType.REST
    assert client.protocol.method == RequestMethod.GET
    assert client.adapter is not None
    assert client.oncall is True

def test_search_resource_initialization():
    client = ResourceSearchClient()
    assert hasattr(client, 'search')
    assert hasattr(client.search, 'protocol')
    assert client.search.protocol.type == ProtocolType.REST
    assert hasattr(client.search, 'adapter')
    assert client.search.oncall is True

def test_parameter_mapping():
    client = SimpleSearchClient()
    response = client._execute(query="test", hits=10)
    assert response.request.params == {"query": "test", "hits": 10}

def test_default_parameters():
    client = SimpleSearchClient()
    response = client._execute(query="test")
    assert response.request.params.get('hits') == 20  # Changed from 'per_page'
    assert response.status_code == 200

def test_oncall_execution():
    client = SimpleSearchClient()
    response = client(query="test")
    assert response.request.params.get("query") == "test"  # Changed from "q"
    assert response.status_code == 200

def test_search_resource_execution():
    client = ResourceSearchClient()
    response = client.search.execute(query="test")
    assert response.request.params.get("query") == "test"  # Changed from "q"
    assert response.status_code == 200


def test_invalid_parameters():
    client = SimpleSearchClient()
    with pytest.raises(ValueError):
        client(invalid_param="test")

def test_protocol_type_validation():
    with pytest.raises(ValueError):
        class InvalidClient(SearchClient):
            protocol = "invalid"
        InvalidClient()

def test_multiple_search_resources():
    class MultiSearchClient(Client):
        baseurl = "https://api.test.com"

        @searchresource
        class Products:
            protocol = Protocol(ProtocolType.REST, RequestMethod.GET)
            payload = Payload(
                query=Parameter()  # Will default to "query"
            )
            oncall = True

        @searchresource
        class Users:
            protocol = Protocol(ProtocolType.REST, RequestMethod.GET)
            payload = Payload(
                query=Parameter()  # Will default to "query"
            )
            oncall = True

    client = MultiSearchClient()
    products_response = client.products.execute(query="test")
    users_response = client.users.execute(query="test")
    assert products_response.request.params.get("query") == "test"  # Updated assertion
    assert users_response.request.params.get("query") == "test"    # Updated assertion
    assert products_response.status_code == 200
    assert users_response.status_code == 200
