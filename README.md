# ClientFactory

A declarative framework for building API clients with minimal boilerplate that supports multiple protocols and authentication methods.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
   - [Client and Resources](#client-and-resources)
   - [URL Construction](#url-construction)
   - [Order of Operations in Method Execution](#order-of-operations-in-method-execution)
3. [Features](#features)
   - [Declarative API Definition](#declarative-api-definition)
   - [Authentication Support](#authentication-support)
   - [Multi-Protocol Support](#multi-protocol-support)
   - [Session Management](#session-management)
   - [State Persistence](#state-persistence)
   - [Parameter Handling](#parameter-handling)
   - [Specialized Resources](#specialized-resources)
4. [Installation](#installation)
5. [Usage Example](#usage-example)
6. [Core Concepts](#core-concepts)
7. [Contributing](#contributing)
8. [License](#license)

## Overview

ClientFactory is a Python library designed to streamline the creation and management of API clients by using a declarative syntax. It reduces boilerplate code and provides a structured approach to handle various API protocols, authentication schemes, and session management.

## Architecture

### Client and Resources

In ClientFactory, the `Client` class is central, serving as a container for resources, authentication, and session management. Resources are nested classes within a `Client` class, representing different logical groupings of API endpoints.

- **Automatic Resource Path**: If no path is specified for a resource, it defaults to using the resource's class name in lowercase as the path.
- **Resource Instantiation**: Upon client instantiation, resource instances are accessible as lowercase attributes of the client object. For example:

  ```python
  class ExampleClient(Client):
      class SomeResource(Resource):
          pass

  client = ExampleClient()
  # Access resource by its lowercase name
  client.someresource
  ```

### URL Construction

ClientFactory automates the construction of API request URLs:

- **Base URL**: Defined at the `Client` level.
- **Resource Path**: Each resource class appends its path to the base URL.
- **Method Path and Parameters**: Methods can specify additional paths and parameters, replacing placeholders with method arguments.

### Order of Operations in Method Execution

The sequence of operations for method execution includes:
1. **Path Construction**: Combining base URL, resource, and method paths. Placeholders in the path are replaced by actual method arguments.
2. **Payload Preparation**: Validating and transforming the method's payload.
3. **Request Processing**: Applying preprocessors and configuring request headers and parameters.
4. **Authentication Enforcement**: Appending authentication details to the request if required.
5. **Request Execution**: Sending the HTTP request.
6. **Response Handling**: Applying postprocessors and returning the response.

Below is a visual representation of these operations:

```plaintext
+------------------+
|      Client      |
| (baseurl: ...)   |
+------------------+
          |
          v
+------------------+     +--------------------------+
|     Resource     |     |         Session          |
| (path: /api)     |<--> | (auth, headers, cookies) |
+------------------+     +--------------------------+
        |
        v
+-------------------+    +----------------------+
|   ResourceMethod  |--> | URL Construction     |
| (e.g., get_user)  |    +----------------------+
| @get("{id}")      |    +----------------------+
+-------------------+--> | Payload Validation   |
                         +----------------------+
...                    -->| Preprocessing       |
                         +----------------------+
                         | Authentication       |
                         +----------------------+
                         | Request Execution    | --> {API Request}
                         +----------------------+
                         | Postprocessing       |
                         +----------------------+
                         | Response Handling    | <-- {API Response}
                         +----------------------+
                         | Return to Method     |
                         +----------------------+
```

## Features

### Declarative API Definition

Easily define API clients using classes and decorators:

```python
from clientfactory import Client, resource, get, post

class ExampleClient(Client):
    baseurl = "https://api.example.com"

    @resource
    class Users:
        @get("{id}")
        def get_user(self, id): pass

        @post
        def create_user(self, **data): pass
```

### Authentication Support

ClientFactory supports various authentication strategies including:

- **Bearer Token**
- **Basic Auth**
- **API Key** (can be sent in the header or as a query string)
- **OAuth 2.0** (supports multiple OAuth flows)
- **DPoP** (Demonstration of Proof-of-Possession)

### Multi-Protocol Support

Leverage different protocol backends:

- **REST**: Basic HTTP protocols with method decorators.
- **GraphQL**: Easily define GraphQL queries and operations.
- **Algolia**: Optimized search request handling.

### Session Management

- **Enhanced Sessions**: Allows for state management, persistent cookie storage, and dynamic header settings.

### State Persistence

Maintain and persist session state across requests using JSON or Pickle files:

```python
from clientfactory.session.state import JSONStateStore
from clientfactory.decorators import jsonstore

@jsonstore
class StateManager:
    path = "session_state.json"
```

### Parameter Handling

Schemas define validation and transformation rules for request data, ensuring consistency and reducing potential errors. Automatic docstring construction is provided for payloads, offering clear guidance on required and optional parameters.

### Specialized Resources

#### Search Resources

Use `searchresource` to create search functionality. The `search` method is dynamically generated unless specified with `oncall` to make the resource a callable object.

```python
class SearchClient(Client):
    @searchresource
    class AdvancedSearch:
        oncall = True
```

Call via `client.advancedsearch()` if `oncall` is `True`, otherwise use `client.advancedsearch.search()`.

#### Managed Resources (CRUD)

Predefined CRUD operations using a structured interface:

```python
from clientfactory import Client, managedresource

class CRUDClient(Client):
    baseurl = "https://api.example.com"

    @managedresource
    class Users:
        operations = {
            "create": createop(payload=user_payload),
            "get": readop("{id}"),
            "update": updateop("{id}", payload=user_payload),
            "delete": deleteop("{id}"),
            "list": listop()
        }
```

## Installation

Install ClientFactory using pip:

```bash
pip install clientfactory
```

## Usage Example

Here’s a complete example defining and using a client with authentication and resource methods:

```python
from clientfactory import Client, resource, get, post
from clientfactory.auth import TokenAuth

class ExampleClient(Client):
    baseurl = "https://api.example.com"
    auth = TokenAuth.Bearer("access-token")

    @resource
    class Users:
        @get("{id}")
        def get_user(self, id):
            """Retrieve a user by ID"""
            pass

        @post
        def create_user(self, **data):
            """Create a new user"""
            pass

client = ExampleClient()

# Retrieve a user by ID
user_response = client.users.get_user(id=1)

# Create a new user
create_response = client.users.create_user(name="John Doe", email="john@example.com")
```

## Core Concepts

- **Client**: The container managing resources, authentication, and session settings.
- **Resource**: Encapsulates related API endpoints as methods, with automatic URL construction and Payload handling.
- **Payload**: Manages the schema for request parameters, enforcing validation and transformation rules.
- **Auth**: Configures various authentication schemes to ensure secure API communication.
- **Session**: Manages state and communication context between requests.
- **Backend**: Handles different protocols, allowing for flexibility and custom integrations (e.g., REST, GraphQL).

## Contributing

Contributions are welcome! Feel free to submit a Pull Request with enhancements, features, or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

This expanded readme now includes detailed guidance on architecture, url construction, method execution sequence, and specifics about resource management, providing deeper insights for developers using ClientFactory.
