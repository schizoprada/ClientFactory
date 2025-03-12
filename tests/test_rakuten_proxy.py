# ~/ClientFactory/tests/test_rakuten_proxy.py
import pytest
from collections import OrderedDict
import urllib.parse
from clientfactory import Client, Request, RequestMethod
from clientfactory.transformers import TransformPipeline
from clientfactory.clients.search import Parameter, Payload, Protocol, ProtocolType, searchresource
from clientfactory.clients.search.transformers import PayloadTransform, URLTransform, ProxyTransform

class TestRakutenProxy:
    APIURL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
    APIKEY = "test_key"
    BASEURL = "https://webservice.rakuten.co.jp/explorer/proxy"

    def test_proxy_transform_chain(self):
        input_params = OrderedDict([
            ("keyword", "test"),
            ("sort", "standard"),
            ("format", "json")
        ])

        # Build URL with sorted params
        params = OrderedDict(sorted(input_params.items()))
        expected_url = f"{self.APIURL}?{urllib.parse.urlencode(params)}"

        pipeline = TransformPipeline([
            PayloadTransform("params", {}),  # No default params, use input_params order
            URLTransform("url", self.APIURL),
            ProxyTransform(
                apiurl=self.APIURL,
                valmap={"url": "url", "applicationId": "apikey"},
                apikey=self.APIKEY
            )
        ])

        result = pipeline(input_params)

        assert result == {
            "url": expected_url,
            "applicationId": self.APIKEY
        }

    def test_full_client_request(self):
        class TestRakuten(Client):
            baseurl = TestRakutenProxy.BASEURL

            @searchresource
            class Search:
                transforms = [
                    PayloadTransform("params", {"format": "json"}),
                    URLTransform("url", TestRakutenProxy.APIURL),
                    ProxyTransform(
                        apiurl=TestRakutenProxy.APIURL,
                        valmap={"url": "url", "applicationId": "apikey"},
                        apikey=TestRakutenProxy.APIKEY
                    )
                ]
                protocol = Protocol(ProtocolType.REST, RequestMethod.GET)
                payload = Payload(
                    keyword=Parameter(),
                    sort=Parameter(default="standard")
                )
                oncall = True

                # Override _execute to return request instead of response
                def _execute(self, **kwargs):
                    params = kwargs
                    if hasattr(self._config, 'pipeline'):
                        params = self._config.pipeline(params)

                    return Request(
                        method=RequestMethod.GET,
                        url=self.baseurl,
                        params=params
                    )

        client = TestRakuten()
        request = client.search._execute(keyword="test")

        params = OrderedDict(sorted(request.params.items()))
        assert "url" in params
        assert params["applicationId"] == self.APIKEY
        assert self.APIURL in params["url"]
