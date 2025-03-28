# ~/ClientFactory/src/clientfactory/utils/internal/__init__.py

from .attribution import (
    attributes, Attributer
)

from clientfactory.log import log
log.remove()

__all__ =[
    'attributes',
    'Attributer'
]
