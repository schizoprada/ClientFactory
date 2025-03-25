# ~/ClientFactory/tests/unit/auth/test_declarative.py
from __future__ import annotations
import pytest
from datetime import datetime, timedelta

from clientfactory.auth import (
    BaseAuth, BasicAuth, APIKeyAuth, TokenAuth, OAuthAuth,
    TokenScheme, KeyLocation, OAuthConfig, OAuthFlow
)
from clientfactory.decorators.auth import authprovider, auth

def test_base_declarative_attributes():
    """Test basic declarative attribute processing"""
    @authprovider
    class CustomAuth(BaseAuth):
        name = "custom"
        value = "test"

    assert CustomAuth.getmetadata('name') == "custom"
    assert CustomAuth.getmetadata('value') == "test"

    instance = CustomAuth()
    assert instance.name == "custom"
    assert instance.value == "test"

def test_basic_auth_declarative():
    """Test BasicAuth declarative functionality"""
    @auth.basic
    class MyBasic:
        username = "testuser"
        password = "testpass"

    auth_instance = MyBasic()
    assert auth_instance.username == "testuser"
    assert auth_instance.password == "testpass"

    # Test override via init
    auth_override = MyBasic(username="override")
    assert auth_override.username == "override"
    assert auth_override.password == "testpass"

def test_apikey_auth_declarative():
    """Test APIKeyAuth declarative functionality"""
    @auth.apikey
    class MyAPIKey:
        key = "test-key"
        name = "X-Test-Key"
        location = KeyLocation.HEADER
        prefix = "Test"

    auth_instance = MyAPIKey()
    assert auth_instance.key == "test-key"
    assert auth_instance.name == "X-Test-Key"
    assert auth_instance.location == KeyLocation.HEADER
    assert auth_instance.prefix == "Test"

    # Test override via init
    auth_override = MyAPIKey(key="new-key", location=KeyLocation.QUERY)
    assert auth_override.key == "new-key"
    assert auth_override.location == KeyLocation.QUERY
    assert auth_override.name == "X-Test-Key"  # Unchanged

def test_token_auth_declarative():
    """Test TokenAuth declarative functionality"""
    @auth.token
    class MyToken:
        token = "test-token"
        scheme = TokenScheme.BEARER
        expiresin = 3600

    auth_instance = MyToken()
    assert auth_instance.token == "test-token"
    assert auth_instance.scheme == TokenScheme.BEARER
    assert auth_instance.expiresin == 3600

    # Verify state is set correctly
    assert auth_instance.state.token == "test-token"
    assert auth_instance.state.authenticated is True

def test_oauth_auth_declarative():
    """Test OAuthAuth declarative functionality"""
    @auth.oauth
    class MyOAuth:
        clientid = "test-client"
        clientsecret = "test-secret"
        tokenurl = "https://test.com/token"
        authurl = "https://test.com/auth"
        scope = "read write"
        flow = OAuthFlow.CLIENTCREDENTIALS

    auth_instance = MyOAuth()
    assert isinstance(auth_instance.config, OAuthConfig)
    assert auth_instance.config.clientid == "test-client"
    assert auth_instance.config.clientsecret == "test-secret"
    assert auth_instance.config.tokenurl == "https://test.com/token"
    assert auth_instance.config.authurl == "https://test.com/auth"
    assert auth_instance.config.scope == "read write"
    assert auth_instance.config.flow == OAuthFlow.CLIENTCREDENTIALS

def test_auth_inheritance():
    """Test that declarative attributes are properly inherited"""
    @authprovider
    class BaseCustomAuth(BaseAuth):
        shared = "base"
        overridden = "base"

    @authprovider
    class ChildCustomAuth(BaseCustomAuth):
        overridden = "child"
        new = "child"

    instance = ChildCustomAuth()
    assert instance.shared == "base"
    assert instance.overridden == "child"
    assert instance.new == "child"

def test_invalid_auth_type():
    """Test that invalid auth types are caught"""
    with pytest.raises(Exception) as exc:
        @authprovider(authtype=str)  # str is not a valid auth type
        class InvalidAuth:
            pass
    assert "Invalid authtype" in str(exc.value)

def test_constructor_override():
    """Test that constructor arguments properly override declarative attributes"""
    @auth.apikey
    class ConfigurableAuth:
        key = "default"
        name = "X-API-Key"
        location = KeyLocation.HEADER

    # Test defaults
    default_instance = ConfigurableAuth()
    assert default_instance.key == "default"

    # Test constructor override
    override_instance = ConfigurableAuth(
        key="override",
        name="X-Custom",
        location=KeyLocation.QUERY
    )
    assert override_instance.key == "override"
    assert override_instance.name == "X-Custom"
    assert override_instance.location == KeyLocation.QUERY

def test_metadata_access():
    """Test that metadata can be accessed and modified"""
    @authprovider
    class MetadataAuth(BaseAuth):
        test_value = "original"

    assert MetadataAuth.getmetadata('test_value') == "original"

    # Test metadata modification
    MetadataAuth.setmetadata('new_value', 'test')
    assert MetadataAuth.getmetadata('new_value') == 'test'
