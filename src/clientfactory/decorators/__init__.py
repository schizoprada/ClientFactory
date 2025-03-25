# ~/ClientFactory/src/clientfactory/decorators/__init__.py
"""
Decorator Methods
"""
from .resource import (
    resource, searchresource, managedresource
)

from .method import (
    httpmethod, methodwithpayload, get,
    post, put, patch,
    delete, head, options
)

from .transform import (
    preprocess, postprocess,
    transformrequest, transformresponse
)

from .validation import (
    validateinput, validateoutput
)

from .auth import (
    authprovider, auth
)

from .client import clientclass

__all__ = [
    'httpmethod', 'methodwithpayload', 'get',
    'post', 'put', 'patch',
    'delete', 'head', 'options',
    'preprocess', 'postprocess', 'transformrequest',
    'transformresponse', 'validateinput', 'validateoutput',
    'resource', 'searchresource', 'managedresource',
    'authprovider', 'auth'
]
