# ~/ClientFactory/tests/test_search_adapters.py
import pytest
from clientfactory.clients.search.adapters import (
    REST, RESTConfig, PaginationStyle, FilterStyle,
    Algolia, AlgoliaConfig, AlgoliaSort,
    GraphQL, GQLConfig, GQLOps
)

# REST Adapter Tests
class TestRESTAdapter:
    @pytest.fixture
    def adapter(self):
        return REST()

    def test_basic_params(self, adapter):
        params = {"query": "test", "category": "shoes"}
        result = adapter.formatparams(params)
        assert result == params  # Default mapping should preserve names

    def test_param_mapping(self):
        config = RESTConfig(paramsmap={"query": "q", "hits": "per_page"})
        adapter = REST(config=config)
        result = adapter.formatparams({"query": "test", "hits": 20})
        assert result == {"q": "test", "per_page": 20}

    def test_filter_styles(self):
        # Test each filter style
        params = {"color": "red", "size": "large"}

        # IDX style
        idx_config = RESTConfig(filterstyle=FilterStyle.IDX)
        idx_adapter = REST(config=idx_config)
        assert idx_adapter.formatfilters(params) == {
            "filter[color]": "red",
            "filter[size]": "large"
        }

        # KV style
        kv_config = RESTConfig(filterstyle=FilterStyle.KV)
        kv_adapter = REST(config=kv_config)
        assert kv_adapter.formatfilters(params)["filter"].split(" ") == [
            "color:red",
            "size:large"
        ]

        # EQ style
        eq_config = RESTConfig(filterstyle=FilterStyle.EQ)
        eq_adapter = REST(config=eq_config)
        assert eq_adapter.formatfilters(params) == params

    def test_pagination_styles(self):
        # Test each pagination style
        page, hits = 2, 20

        # NUMBER style
        num_config = RESTConfig(paginationstyle=PaginationStyle.NUMBER)
        num_adapter = REST(config=num_config)
        assert num_adapter.formatpagination(page, hits) == {
            "page": 2,
            "hits": 20
        }

        # OFFSET style
        off_config = RESTConfig(paginationstyle=PaginationStyle.OFFSET)
        off_adapter = REST(config=off_config)
        assert off_adapter.formatpagination(page, hits) == {
            "offset": 20,
            "limit": 20
        }

        # CURSOR style
        cur_config = RESTConfig(paginationstyle=PaginationStyle.CURSOR)
        cur_adapter = REST(config=cur_config)
        assert cur_adapter.formatpagination(page, hits, cursor="abc123") == {
            "cursor": "abc123",
            "limit": 20
        }

# Algolia Adapter Tests
class TestAlgoliaAdapter:
    @pytest.fixture
    def adapter(self):
        a = Algolia()
        a.config.index = "test_index"
        return a

    def test_basic_params(self, adapter):
        params = {"query": "test"}
        result = adapter.formatall(params=params)
        assert "requests" in result
        assert "params" in result["requests"][0]
        assert result["requests"][0]["params"] == params

    def test_index_handling(self):
        # Test index priority
        config = AlgoliaConfig(index="default_index")
        adapter = Algolia(config=config)

        # Default index
        result = adapter.formatall(params={"query": "test"})
        assert result["requests"][0]["indexName"] == "default_index"

        # Explicit index
        result = adapter.formatall(params={"query": "test"}, index="explicit_index")
        assert result["requests"][0]["indexName"] == "explicit_index"

    def test_sorting_modes(self):
        # Test different sorting modes
        basic_config = AlgoliaConfig(sortmode=AlgoliaSort.BASIC)
        basic_adapter = Algolia(config=basic_config)
        assert basic_adapter.formatsorting("price", "desc") == {
            "ranking": ["price:desc"]
        }

        # Test replica sorting
        replica_config = AlgoliaConfig(
            sortmode=AlgoliaSort.REPLICA,
            replicas={"price": "products_price_desc"}
        )
        replica_adapter = Algolia(config=replica_config)
        assert replica_adapter.formatsorting("price", "desc") == {}

# GraphQL Adapter Tests
class TestGraphQLAdapter:
    @pytest.fixture
    def adapter(self):
        return GraphQL()

    def test_basic_params(self, adapter):
        params = {"query": "test"}
        result = adapter.formatparams(params)
        assert result == {"variables": params}

    def test_filter_operations(self, adapter):
        filters = {
            "price": {"gt": 100},
            "category": "shoes"  # Simple equality
        }
        result = adapter.formatfilters(filters)
        assert result["variables"]["filter"]["price"] == {"gt": 100}
        assert result["variables"]["filter"]["category"] == {"eq": "shoes"}

    def test_complete_query(self):
        config = GQLConfig(
            operation="ProductSearch",
            query="query ProductSearch($query: String!) { products(query: $query) { id name } }"
        )
        adapter = GraphQL(config=config)
        # Add params key since formatall expects it
        result = adapter.formatall(params={"query": "test"})
        assert result["operationName"] == "ProductSearch"
        assert "query" in result
        assert "variables" in result
        assert result["variables"]["query"] == "test"

def test_cross_adapter_compatibility():
    """Test that different adapters can handle similar input parameters"""
    params = {
        "query": "test",
        "page": 2,
        "hits": 20,
        "sort": "price",
        "order": "desc"
    }

    rest = REST()
    algolia = Algolia(config=AlgoliaConfig(index="products"))
    graphql = GraphQL()

    # Test REST formatting
    rest_result = rest.formatall(**params)
    assert rest_result.get("sort") == "price"
    assert rest_result.get("order") == "desc"

    # Test Algolia formatting
    algolia_result = algolia.formatall(**params)
    assert "requests" in algolia_result
    assert "ranking" in algolia_result["requests"][0]["params"]
    assert algolia_result["requests"][0]["params"]["ranking"] == ["price:desc"]

    # Test GraphQL formatting
    graphql_result = graphql.formatall(**params)
    assert "variables" in graphql_result
    assert graphql_result["variables"]["sort"] == {
        "field": "price",
        "order": "DESC"
    }
