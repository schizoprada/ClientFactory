# ~/ClientFactory/tests/unit/resources/test_managed.py
from __future__ import annotations
import pytest

from clientfactory.core.request import RequestMethod as RM
from clientfactory.core.payload import Payload
from clientfactory.core.session import Session
from clientfactory.resources.managed import (
    ManagedResource, ManagedResourceConfig,
    Operation, OperationType,
    createop, readop, updateop, deleteop, listop
)
from clientfactory.decorators import managedresource

def test_managed_resource_metadata():
    """Test that managed resource attributes are properly processed into metadata"""
    class CustomManaged(ManagedResource):
        operations = {
            'create': createop(payload=Payload()),
            'list': listop(),
            'get': readop(),
            'update': updateop(),
            'delete': deleteop()
        }

    ops = CustomManaged.getmetadata('operations')
    assert len(ops) == 5
    assert all(isinstance(op, Operation) for op in ops.values())
    assert ops['create'].type == OperationType.CREATE
    assert ops['list'].type == OperationType.LIST

def test_managed_resource_decorator():
    """Test the @managedresource decorator"""
    @managedresource(path="users")
    class Users:
        operations = {
            'create': createop(),
            'list': listop()
        }

    assert issubclass(Users, ManagedResource)
    assert Users.getmetadata('path') == "users"
    assert len(Users.getmetadata('operations')) == 2

def test_operation_setup():
    """Test that operations are properly configured as methods"""
    class CustomManaged(ManagedResource):
        operations = {
            'create': createop(payload=Payload()),
            'list': listop()
        }

    session = Session()
    config = ManagedResourceConfig(
        name="users",
        path="users"
    )

    resource = CustomManaged(session, config)

    # Check that methods were created
    assert hasattr(resource, "create")
    assert hasattr(resource, "list")

    # Check method configurations
    assert "create" in resource._config.methods
    assert "list" in resource._config.methods

    create_config = resource._config.methods["create"]
    assert create_config.method == RM.POST
    assert isinstance(create_config.payload, Payload)

    list_config = resource._config.methods["list"]
    assert list_config.method == RM.GET
