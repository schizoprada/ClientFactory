# ~/ClientFactory/src/clientfactory/decorators/__init__.py
"""
Decorator Methods
"""
from .resource import (
    resource, subresource
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

__all__ = [
    'httpmethod', 'methodwithpayload', 'get',
    'post', 'put', 'patch',
    'delete', 'head', 'options',
    'preprocess', 'postprocess', 'transformrequest',
    'transformresponse', 'validateinput', 'validateoutput'
]
