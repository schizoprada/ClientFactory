# ~/ClientFactory/tests/test_proxy_transform.py
import pytest
from clientfactory.transformers import Transform, TransformPipeline
from clientfactory.clients.search.transformers import PayloadTransform, ProxyTransform
import urllib.parse

class TestRakutenTransforms:
    # Test data matching Rakuten's structure
    CONDITIONS = {
        "keyword": None,
        "tagId": None,
        "genreId": None,
        "minPrice": None,
        "maxPrice": None,
        "sort": "standard",
        "order": "-"
    }

    ARGS = {
        "format": "json",
        "hits": 30,
        "page": 1
    }

    APIURL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
    APIKEY = "test-api-key"

    def test_single_transform_conditions(self):
        """Test PayloadTransform with conditions"""
        transform = PayloadTransform("conditions", self.CONDITIONS)
        result = transform({"keyword": "test", "tagId": "123"})

        assert result["keyword"] == "test"
        assert result["tagId"] == "123"
        assert result["sort"] == "standard"  # default value
        assert result["order"] == "-"  # default value

    def test_single_transform_args(self):
        """Test PayloadTransform with args"""
        transform = PayloadTransform("args", self.ARGS)
        result = transform({"page": 2})

        assert result["format"] == "json"
        assert result["hits"] == 30
        assert result["page"] == 2  # overridden value

    def test_single_transform_proxy(self):
        """Test ProxyTransform"""
        transform = ProxyTransform(
            apiurl=self.APIURL,
            valmap={
                "url": "url",
                "applicationId": "apikey"
            },
            apikey=self.APIKEY
        )

        params = {"keyword": "test", "format": "json"}
        result = transform(params)

        assert "url" in result
        assert "applicationId" in result
        assert result["applicationId"] == self.APIKEY
        assert self.APIURL in result["url"]
        assert "keyword=test" in result["url"]
        assert "format=json" in result["url"]

    def test_transform_pipeline(self):
        """Test full transform pipeline"""
        pipeline = TransformPipeline([
            PayloadTransform("conditions", self.CONDITIONS),
            PayloadTransform("args", self.ARGS),
            ProxyTransform(
                apiurl=self.APIURL,
                valmap={
                    "url": "url",
                    "applicationId": "apikey"
                },
                apikey=self.APIKEY
            )
        ])

        # Input params similar to what we'd pass to Rakuten search
        search_params = {
            "keyword": "vetements",
            "tagId": "123",
            "page": 2
        }

        result = pipeline(search_params)

        # Verify the final structure
        assert "url" in result
        assert "applicationId" in result
        assert result["applicationId"] == self.APIKEY

        # Parse the URL to check parameters
        parsed_url = urllib.parse.urlparse(result["url"])
        query_params = dict(urllib.parse.parse_qsl(parsed_url.query))

        # Check if all parameters are present with correct values
        assert query_params["keyword"] == "vetements"
        assert query_params["tagId"] == "123"
        assert query_params["page"] == "2"
        assert query_params["format"] == "json"
        assert query_params["hits"] == "30"
        assert query_params["sort"] == "standard"
        assert query_params["order"] == "-"

    def test_proxy_transform_url_handling(self):
        """Test ProxyTransform handles URLs correctly"""
        transform = ProxyTransform(
            apiurl=self.APIURL,
            valmap={"url": "url"}
        )

        # Test with various URL formats
        cases = [
            ({"param": "value"}, f"{self.APIURL}?param=value"),
            ({}, f"{self.APIURL}?"),
            ({"a": 1, "b": 2}, f"{self.APIURL}?a=1&b=2")
        ]

        for params, expected_url in cases:
            result = transform(params)
            assert result["url"].rstrip("?") == expected_url.rstrip("?")

    def test_proxy_transform_custom_mapping(self):
        """Test ProxyTransform with custom value mapping"""
        transform = ProxyTransform(
            apiurl=self.APIURL,
            valmap={
                "proxy_url": "url",
                "token": "apikey",
                "client": "client_id"
            },
            apikey="test-key",
            client_id="test-client"
        )

        result = transform({"param": "value"})

        assert "proxy_url" in result
        assert result["token"] == "test-key"
        assert result["client"] == "test-client"
