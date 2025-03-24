# ~/ClientFactory/tests/unit/client/test_config.py
"""
Pytest configuration for client tests.
"""
import pytest
from unittest.mock import MagicMock

from clientfactory.core import Session, ResourceConfig
from clientfactory.core.request import RequestMethod
from clientfactory.core.resource import MethodConfig


@pytest.fixture
def mock_session():
    """Return a mock session"""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_resource_config():
    """Return a mock resource configuration"""
    config = ResourceConfig(
        name="TestResource",
        path="testresource"
    )

    # Add a test method
    config.methods["test"] = MethodConfig(
        name="test",
        method=RequestMethod.GET
    )

    return config


@pytest.fixture
def mock_resource_class():
    """Return a mock resource class with resourceconfig"""
    cls = MagicMock()
    cls.__name__ = "TestResource"
    cls._resourceconfig = mock_resource_config()
    return cls
