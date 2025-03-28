"""
Validation Decorators
---------------------
Provides decorators for validating request inputs and response outputs.
"""
import typing as t, functools as fn
from clientfactory.log import log

from clientfactory.core.request import Request
from clientfactory.core.response import Response

class ValidationError(Exception):
    """Raised when validation fails."""
    pass

def validateinput(validator: t.Callable[[dict], dict]):
    """
    Decorator to validate and potentially transform input parameters.

    The validator function receives the kwargs dictionary and should:
    - Validate the inputs, raising ValidationError if invalid
    - Return the validated (and potentially transformed) inputs
    """
    def decorator(method):
        @fn.wraps(method)
        def wrapper(*args, **kwargs):
            # The first argument could be 'self' if it's a method in a class
            # We don't need to pass it to the validator
            try:
                validated = validator(kwargs)
                kwargs.update(validated)
            except ValidationError as e:
                raise

            # Pass all arguments to the original method
            return method(*args, **kwargs)
        return wrapper
    return decorator

def validateoutput(validator: t.Callable[[Response], t.Any]):
    """
    Decorator to validate and potentially transform the response.

    The validator function receives the Response object and should:
    - Validate the response, raising ValidationError if invalid
    - Return the validated (and potentially transformed) response
    """
    from clientfactory.decorators.transform import postprocess

    # Store validator for later use without executing it now
    return postprocess(validator)
