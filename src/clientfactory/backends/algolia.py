# ~/ClientFactory/src/clientfactory/backends/algolia.py
from __future__ import annotations
import enum, json, typing as t
import urllib.parse
from dataclasses import dataclass, field

from clientfactory.core.request import Request, RequestMethod
from clientfactory.core.response import Response
from clientfactory.backends.base import Backend, BackendType

@dataclass
class AlgoliaConfig:
    """Configuration for Algolia requests"""
    appid: str
    apikey: str
    indices: t.List[str]
    agent: str = "Algolia for JavaScript (4.14.3); Browser; JS Helper (3.22.5); react (18.2.0); react-instantsearch (6.39.1)"

    @property
    def endpoint(self) -> str:
        endpoint = f"https://{self.appid}-dsn.algolia.net/1/indexes/*/queries"
        #print(f"\nAlgoliaConfig.endpoint:")
        #print(f"Generated endpoint: {endpoint}")
        return endpoint

    @property
    def headers(self) -> dict:
        """Get required Algolia headers"""
        headers = {
            'x-algolia-api-key': self.apikey,
            'x-algolia-application-id': self.appid,
            'content-type': 'application/x-www-form-urlencoded'
        }
        #print(f"\nAlgoliaConfig.headers:")
        #print(f"Generated headers: {headers}")
        return headers

class AlgoliaError(Exception):
    pass

class Algolia(Backend):
    """
    Algolia backend protocol adapter.
    """
    __declarativetype__ = 'algolia'

    def __init__(
        self,
        config: t.Optional[AlgoliaConfig] = None,
        appid: t.Optional[str] = None,
        apikey: t.Optional[str] = None,
        indices: t.Optional[list[str]] = None
    ):
        #print(f"\nAlgolia.__init__:")
        #print(f"Initializing with:")
        #print(f"config: {config}")
        #print(f"appid: {appid}")
        #print(f"apikey: {apikey}")
        #print(f"indices: {indices}")

        super().__init__(BackendType.ALGOLIA, RequestMethod.POST)
        if config is None:
            if not all((appid, apikey, indices)):
                raise AlgoliaError("Algolia requires either AlgoliaConfig or appid+apikey+indices")
            config = AlgoliaConfig(
                appid=appid,
                apikey=apikey,
                indices=indices
            )
        self.config = config
        #print(f"Initialized with config: {self.config}")

    def preparerequest(self, request: Request, data: dict) -> Request:
        #print(f"\nAlgolia.preparerequest:")
        #print(f"Initial request: {request}")
        #print(f"Received data: {data}")

        requests = [
            {
                "indexName": index,
                "params": urllib.parse.urlencode(request.params)
            }
            for index in self.config.indices
        ]
        #print(f"Built requests array: {requests}")

        payload = {
            "requests": requests
        }
        #print(f"Created payload: {payload}")

        agentparam = urllib.parse.urlencode({'x-algolia-agent': self.config.agent})
        url = f"{self.config.endpoint}?{agentparam}"
        #print(f"Constructed URL: {url}")

        headers = dict(request.headers or {})
        headers.update(self.config.headers)
        #print(f"Final headers: {headers}")



        cloned = request.clone(
            method=RequestMethod.POST,
            url=url,
            headers=headers,
            data=json.dumps(payload),
            params={}
        )
        #print(f"Final request: {cloned}")
        return cloned

    def _responseprocessor(self, response: Response) -> t.Any:
        """Process Algolia response"""
        #print(f"\nAlgolia._responseprocessor:")
        #print(f"Processing response: {response}")
        #print(f"Status code: {response.statuscode}")

        if not response.ok:
            #print(f"Response not OK, raising for status")
            response.raiseforstatus()

        data = response.json()
        #print(f"Response data: {data}")

        if "message" in data and "status" in data and data["status"] >= 400:
            #print(f"Error in response: {data['message']}")
            raise AlgoliaError(f"Algolia Error: {data['message']}")

        results = data.get('results', data)
        #print(f"Returning results: {results}")
        return results
