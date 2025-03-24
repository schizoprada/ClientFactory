# ~/ClientFactory/tests/integration/declarative/test_integration.py
import pytest
from clientfactory.declarative import (
    DeclarativeClient, DeclarativeResource,
    client, resource, declarativemethod
)

def test_complete_api_definition():
    """Test complete API definition using declarative components"""
    @client(baseurl="https://api.test.com")
    class TestAPI:
        @resource(path="/users")
        class Users:
            @declarativemethod
            def list(self):
                """Get all users"""
                pass

            @declarativemethod
            def get(self, id):
                """Get user by ID"""
                pass

        @resource(path="/posts")
        class Posts:
            @declarativemethod
            def create(self, data):
                """Create new post"""
                pass

            @resource(path="{id}/comments")
            class Comments:
                @declarativemethod
                def list(self, id):
                    """List comments for post"""
                    pass

    # Verify structure
    assert TestAPI.getbaseurl() == "https://api.test.com"
    assert 'users' in TestAPI.getresources()
    assert 'posts' in TestAPI.getresources()

    # Verify paths
    users = TestAPI.getresources()['users']
    posts = TestAPI.getresources()['posts']
    comments = posts.getnestedresources()['comments']

    assert users.getfullpath() == "/users"
    assert posts.getfullpath() == "/posts"
    assert comments.getfullpath() == "/posts/{id}/comments"

    # Verify methods
    assert 'list' in users.getmethods()
    assert 'get' in users.getmethods()
    assert 'create' in posts.getmethods()
    assert 'list' in comments.getmethods()

def test_auth_integration():
    """Test integration with authentication"""
    @client(baseurl="https://api.test.com")
    class AuthAPI:
        auth_type = "bearer"
        auth_token = "test_token"

        @resource
        class Protected:
            @declarativemethod
            def secure_method(self):
                pass

    assert AuthAPI.getmetadata('auth_type') == "bearer"
    assert AuthAPI.getmetadata('auth_token') == "test_token"
    assert 'protected' in AuthAPI.getresources()

def test_nested_resource_integration():
    """Test deeply nested resource structure"""
    @client
    class NestedAPI:
        @resource(path="/a")
        class A:
            @resource(path="b")
            class B:
                @resource(path="c")
                class C:
                    @declarativemethod
                    def method(self):
                        pass

    c_resource = NestedAPI.getresources()['a'].getnestedresources()['b'].getnestedresources()['c']
    assert c_resource.getfullpath() == "/a/b/c"
    assert 'method' in c_resource.getmethods()
