# ~/clientfactory/examples/wix.py
import os, json, mimetypes, typing as t
from client import Client, ClientConfig
from resources import Resource, ResourceConfig, resource, get, post, put, delete, patch, preprocess, postprocess
from session import SessionConfig
from auth import ApiKeyAuth
from utils import Request, Response
import requests as rq
from loguru import logger as log

class Configs:
    Session = SessionConfig(
        headers = {
            'Content-Type': 'application/json',
            'wix-account-id': os.getenv('wixaccountid'),
            'wix-site-id': os.getenv('wixsiteid')
        }
    )


class Wix(Client):
    baseurl = "https://www.wixapis.com"
    auth = ApiKeyAuth.header(
        key=os.getenv('wixmasterkey'),
        name="Authorization"
    ) # will inject into session headers as f"Authorization {key}"
    config = ClientConfig(
        session=Configs.Session
    ) # will inject headers into our session

    @resource
    class Catalog:
        path = "stores/v1/products"
        def queryprocessor(self, request: Request) -> Request:
            if hasattr(request, 'kwargs'):
                return request.WITH(
                    json={
                        "query": {
                            "sort": json.dumps([{"numericId": "asc"}]),  # Convert to JSON string
                            "filter": json.dumps({"numericId": {"$gt": request.kwargs.get('filter', {}).get('numericId', {}).get('$gt', -1)}})  # Convert to JSON string
                        }
                    },
                    kwargs={}
                )
        @preprocess(queryprocessor)
        @post("query")
        def query(self, sort=None, filter=None) -> Response:
            log.debug(f"Catalog.query called with sort={sort}, filter={filter}")
            pass
        @get("{id}")
        def get(self, id:str) -> Response: pass
        @post
        def create(self, product: t.Dict) -> Response: return {"product": product}
        @patch("{id}")
        def update(self, id: str, product: t.Dict) -> Response: return {"product": product}
        @delete("{id}")
        def delete(self, id:str) -> Response: pass
        def all(self):
            allproducts = []
            lastid = -1
            while True:
                qfilter = {"numericId": {"$gt": lastid}}
                sort = [{"numericId": "asc"}]
                try:
                    r = self.query(sort=sort, filter=qfilter)
                    r.raise_for_status()
                    data = r.json()
                    products = data.get('products', [])
                    if not products: break
                    allproducts.extend(products)
                    lastid = max((p.get('numericId', lastid) for p in products), default=lastid)
                    if len(products) < 100: break # last page
                except Exception as e:
                    print(f"error: {str(e)}")
                    break
            return allproducts

    @resource
    class Media:
        path = "site-media/v1/files"

        @get
        def list(self) -> Response: pass

        @post("generate-upload-url")
        def getuploadurl(self, filename:str, mimetype:str, labels: t.List[str]) -> Response:
            return {
                "mimeType": mimeType,
                "fileName": filename,
                "labels": labels
            }

        @post("{productid}/media")
        def attachtoproduct(self, productid:str, mediaids: t.List[str]) -> Response:
            return {
                "media": [{"mediaId": mid} for mid in mediaids]
            }

        def upload(self, filepath:str):
            filename = os.path.basename(filepath)
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            sku = filename.split('_')[0]

            uploadurlresponse = self.getuploadurl(filename=filename, mimetype=mimetype, labels=[sku])
            if not uploadurlresponse: return None
            uploadurl = uploadurlresponse.json()["uploadUrl"]

            with open(filepath, 'rb') as f:
                try:
                    r = rq.put(uploadurl, data=f.read(), headers={"Content-Type": mimetype})
                    r.raise_for_status()
                    return r.json()
                except Exception as e:
                    return {'error': str(e)}
    @resource
    class Sites:
        path = "site-list/v2/sites"
        @post("query")
        def list(self) -> Response:
            return {
                "query": {
                    "filter": {"editorType": "EDITOR"},
                    "sort": [{"fieldName": "createdDate", "order": "ASC"}],
                    "cursorPaging": {"limit": 10}
                }
            }
