# ~/ClientFactory/src/clientfactory/core/__init__.py
"""
Core Classes & Components
"""
from .request import (
    RequestMethod, RequestConfig, RequestError,
    Request, RequestFactory, ValidationError as RequestValidationError
)
from .response import (
    ResponseError, HTTPError, ExtractionError,
    Response, ResponseMapper
)
from .session import (
    SessionError, SessionConfig, Session, SessionBuilder
)
from .payload import (
    ParameterType, Parameter, NestedParameter,
    Payload, PayloadBuilder, PayloadTemplate,
    ValidationError as PayloadValidationError,
    NestedPayload, ConditionalParameter,
    StrParam, NumParam, BoolParam,
    ListParam, DictParam, AnyParam

)
from .resource import (
    ResourceError, MethodConfig, ResourceConfig,
    Resource, ResourceBuilder, decoratormethod,
    get, post, put, patch, delete
)

#from clientfactory.log import log
##log.remove() # remove logging during initialization

__all__ = [
    'RequestMethod', 'RequestConfig', 'RequestError',
    'Request', 'RequestFactory', 'RequestValidationError',
    'ResponseError', 'HTTPError', 'ExtractionError',
    'Response', 'ResponseMapper', 'SessionError',
    'SessionConfig', 'Session', 'SessionBuilder',
    'ParameterType', 'Parameter', 'NestedParameter',
    'Payload', 'PayloadBuilder', 'PayloadTemplate',
    'PayloadValidationError', 'ResourceError', 'MethodConfig',
    'ResourceConfig', 'Resource', 'ResourceBuilder',
    'decoratormethod', 'get', 'post',
    'put', 'patch', 'delete', 'NestedPayload',
    'StrParam', 'NumParam', 'BoolParam',
    'ListParam', 'DictParam', 'AnyParam'
]
