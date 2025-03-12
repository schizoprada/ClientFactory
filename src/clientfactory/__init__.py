# ~/clientfactory/src/clientfactory/__init__.py
"""
ClientFactory
------------
A framework for building API clients with minimal boilerplate.
"""

__version__ = "0.6.6"
__author__ = "Joel Yisrael"
__license__ = "MIT"

# Core exports
from clientfactory.client import Client
from clientfactory.builder import ClientBuilder

# Auth exports
from clientfactory.auth import (
    BaseAuth,
    OAuth2Auth,
    SessionAuth,
    ApiKeyAuth,
    TokenAuth,
    BasicAuth,
    NoAuth
)

# Resource exports
from clientfactory.resources import (
    resource,
    get,
    post,
    put,
    patch,
    delete,
    preprocess,
    postprocess
)

# Session exports
from clientfactory.session import (
    BaseSession,
    SessionConfig,
    DiskPersist,
    MemoryPersist
)

# Utils exports
from clientfactory.utils import (
    Request,
    Response,
    RequestMethod,
    FileUpload,
    UploadConfig
)

# Transformer exports
from clientfactory.transformers import (
    TransformType,
    TransformOperation,
    Transform,
    Transformer,
    TransformPipeline,
    ComposedTransform
)

# Search exports
from clientfactory.clients.search import (
    Search,
    SearchResource,
    SearchResourceConfig,
    SearchClient,
    ParameterType,
    Parameter,
    NestedParameter,
    Payload,
    PayloadTemplate,
    Protocol,
    ProtocolType,
    searchmethod,
    searchresource
)

def nolog():
    from loguru import logger
    logger.remove()
    logger.add(lambda msg: None, level='WARNING')

# Define what's available on import *
__all__ = [
    'Client',
    'ClientBuilder',
    # Auth
    'BaseAuth',
    'OAuth2Auth',
    'SessionAuth',
    'ApiKeyAuth',
    'TokenAuth',
    'BasicAuth',
    'NoAuth',
    # Resources
    'resource',
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'preprocess',
    'postprocess',
    # Session
    'BaseSession',
    'SessionConfig',
    'DiskPersist',
    'MemoryPersist',
    # Utils
    'Request',
    'Response',
    'RequestMethod',
    'FileUpload',
    'UploadConfig',
    # Search
    'SearchClient',
    'Parameter',
    'NestedParameter',
    'ParameterType',
    'Payload',
    'PayloadTemplate',
    'Protocol',
    'ProtocolType',
    'searchmethod',
    'searchresource',
]
