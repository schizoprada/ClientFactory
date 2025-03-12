# ~/ClientFactory/src/clientfactory/clients/managed/tests/test_operations.py
import pytest
from clientfactory.utils.request import RequestMethod
from clientfactory.clients.managed.core import (
    OpType, Operation, Operations,
    C, R, U, D
)

def test_operation_creation():
    """Test basic operation creation"""
    op = Operation(
        type=OpType.CREATE,
        method=RequestMethod.POST,
        path="/test"
    )
    assert op.type == OpType.CREATE
    assert op.method == RequestMethod.POST
    assert op.path == "/test"

def test_crud_shortcuts():
    """Test CRUD operation shortcut classes"""
    c = C()
    r = R()
    u = U()
    d = D()

    assert c.type == OpType.CREATE
    assert c.method == RequestMethod.POST

    assert r.type == OpType.READ
    assert r.method == RequestMethod.GET

    assert u.type == OpType.UPDATE
    assert u.method == RequestMethod.PUT

    assert d.type == OpType.DELETE
    assert d.method == RequestMethod.DELETE

def test_operations_collection():
    """Test Operations collection functionality"""
    ops = Operations(
        C(path="/create"),
        R(path="/read")
    )

    # Test automatic naming
    assert "create" in ops.operations
    assert "read" in ops.operations

    # Test get method
    create_op = ops.get("create")
    assert create_op.type == OpType.CREATE
    assert create_op.path == "/create"

    # Test add method
    ops.add("custom", Operation(
        type=OpType.CUSTOM,
        method=RequestMethod.POST,
        path="/custom"
    ))
    assert "custom" in ops.operations

    # Test method chaining
    ops.add("test1", C()).add("test2", R())
    assert "test1" in ops.operations
    assert "test2" in ops.operations

    # Test remove method
    ops.remove("custom")
    assert "custom" not in ops.operations

def test_operation_preprocessing():
    """Test operation preprocessor functionality"""
    def preprocess(request):
        request.headers["Test"] = "Value"
        return request

    op = Operation(
        type=OpType.CREATE,
        method=RequestMethod.POST,
        preprocess=preprocess
    )
    assert op.preprocess == preprocess

def test_operation_postprocessing():
    """Test operation postprocessor functionality"""
    def postprocess(response):
        return response.json()

    op = Operation(
        type=OpType.READ,
        method=RequestMethod.GET,
        postprocess=postprocess
    )
    assert op.postprocess == postprocess

def test_operation_validation():
    """Test operation validators"""
    def validator(data):
        return isinstance(data, dict)

    op = Operation(
        type=OpType.CREATE,
        method=RequestMethod.POST,
        validators=[validator]
    )
    assert validator in op.validators
