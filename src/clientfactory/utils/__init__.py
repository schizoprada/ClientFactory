# utils/__init__.py
from clientfactory.utils.request import Request, RequestMethod, RequestConfig, RequestError
from clientfactory.utils.response import Response, ResponseError, HTTPError
from clientfactory.utils.fileupload import FileUpload, UploadConfig

## RequestMethod Enum members for simplicity
GET = RequestMethod.GET
POST = RequestMethod.POST
PUT = RequestMethod.PUT
PATCH = RequestMethod.PATCH
DELETE = RequestMethod.DELETE
HEAD = RequestMethod.HEAD
OPTIONS = RequestMethod.OPTIONS
NA = RequestMethod.NA


__all__ = [
    'Request', 'Response', 'FileUpload',
    'RequestConfig', 'UploadConfig', 'RequestMethod',
    'RequestError', 'ResponseError', 'HTTPError',
    'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'NA'
]
