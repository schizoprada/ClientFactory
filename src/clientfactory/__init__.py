# ~/ClientFactory/src/clientfactory/__init__.py
"""
ClientFactory
-------------
A declarative framework for building API clients with minimal boilerplate.
"""
__version__ = "0.6.9"
__author__ = "Joel Yisrael"
__license__ = "MIT"

from .auth import (
    NoAuth, AuthError, AuthState,
    BaseAuth, BasicAuth,
    TokenAuth, TokenScheme, TokenError,
    APIKeyAuth, KeyLocation, APIKeyError,
    OAuthToken, OAuthFlow, OAuthConfig,
    OAuthAuth
)

from .client import (
    Client, ClientConfig, ClientError, ClientBuilder
)

from .core import (
    Request, RequestMethod, RequestConfig,
    RequestFactory, RequestError, RequestValidationError,
    Response, ResponseMapper, ResponseError,
    HTTPError, ExtractionError, SessionError,
    Session, SessionConfig, SessionBuilder,
    Parameter, NestedParameter, ParameterType,
    Payload, PayloadBuilder, PayloadTemplate,
    PayloadValidationError, ResourceError, MethodConfig,
    Resource, ResourceConfig, ResourceBuilder,
    NestedPayload
) # using the HTTP decorators from decorators/

from .decorators import (
    resource, searchresource, managedresource,
    authprovider, auth, httpmethod,
    methodwithpayload, get, post,
    put, patch, delete,
    head, options, preprocess,
    postprocess, transformrequest, transformresponse,
    validateinput, validateoutput, #clientclass
)

from .declarative import (
    DeclarativeMeta, DeclarativeComponent, DeclarativeContainer,
    declarative, declarativemethod, container,
    isdeclarative, getclassmetadata, copymetadata
)


from clientfactory.log import log
from loguru import logger

#log.remove()
#logger.remove()

__all__ = [
    # auth
    "NoAuth", "AuthError", "AuthState",
    "BaseAuth", "BasicAuth",
    "TokenAuth", "TokenScheme", "TokenError",
    "APIKeyAuth", "KeyLocation", "APIKeyError",
    "OAuthToken", "OAuthFlow", "OAuthConfig",
    "OAuthAuth",

    # client
    "Client", "ClientConfig", "ClientError", "ClientBuilder",

    # core
    "Request", "RequestMethod", "RequestConfig",
    "RequestFactory", "RequestError", "RequestValidationError",
    "Response", "ResponseMapper", "ResponseError",
    "HTTPError", "ExtractionError", "SessionError",
    "Session", "SessionConfig", "SessionBuilder",
    "Parameter", "NestedParameter", "ParameterType",
    "Payload", "PayloadBuilder", "PayloadTemplate",
    "PayloadValidationError", "ResourceError", "MethodConfig",
    "Resource", "ResourceConfig", "ResourceBuilder", "NestedPayload",

    # decorators
    "resource", "searchresource", "managedresource",
    "authprovider", "auth", "httpmethod",
    "methodwithpayload", "get", "post",
    "put", "patch", "delete",
    "head", "options", "preprocess",
    "postprocess", "transformrequest", "transformresponse",
    "validateinput", "validateoutput", #"clientclass",

    # declarative
    "DeclarativeMeta", "DeclarativeComponent", "DeclarativeContainer",
    "declarative", "declarativemethod", "container",
    "isdeclarative", "getclassmetadata", "copymetadata"
]
