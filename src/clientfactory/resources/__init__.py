# resources/__init__.py
from clientfactory.resources.base import Resource, ResourceConfig
from clientfactory.resources.decorators import resource, get, post, put, patch, delete, preprocess, postprocess

__all__ = [
    'Resource', 'ResourceConfig',
    'resource', 'get', 'post', 'put', 'patch', 'delete',
    'preprocess', 'postprocess'
]
