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

#from .client import clientclass

from .session import (
    statestore, jsonstore, picklestore,
    memorystore, statemanager, headers,
    session, enhancedsession
)

from .backend import (
    backend, graphql, algolia
)

"""from .payload import (
    payload, EMPTY,  # $ for empty params
    # Parameter settings
    name, type, default, required,
    choices, transform, description, validate,
    # Type helpers
    strparam, numparam, boolparam, arrayparam, dateparam,
    # Type shortcuts
    PT  # ParameterType alias
)"""

__all__ = [
    # HTTP Methods
    'httpmethod', 'methodwithpayload', 'get',
    'post', 'put', 'patch',
    'delete', 'head', 'options',

    # Transforms
    'preprocess', 'postprocess', 'transformrequest',
    'transformresponse',

    # Validation
    'validateinput', 'validateoutput',

    # Resources
    'resource', 'searchresource', 'managedresource',

    # Auth
    'authprovider', 'auth',

    # Session
    'statestore', 'jsonstore', 'picklestore',
    'memorystore', 'statemanager', 'headers',
    'enhancedsession',

    # Backend
    'backend', 'graphql', 'algolia'

    # Payload
    #'payload', '$',
    #'name', 'type', 'default', 'required',
    #'choices', 'transform', 'description', 'validate',
    #'strParam', 'numParam', 'boolParam', 'arrayParam', 'dateParam',
    #'PT'
]
