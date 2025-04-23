# ClientFactory

A declarative framework for building API clients with minimal boilerplate that supports multiple protocols and authentication methods.

## Features

### Declarative API Definition
```python
from clientfactory import Client, resource, get, post

class MyClient(Client):
    baseurl = "https://api.example.com"

    @resource
    class Users:
        @get("{id}")
        def get_user(self, id): pass

        @post
        def create_user(self, **data): pass
```

### Multi-Protocol Support

#### GraphQL
```python
from clientfactory import searchresource
from clientfactory.decorators import graphql
from clientfactory.shorthands import PL, P

@graphql
class BACKEND:
    operation = "MyQuery"
    query = """
        query MyQuery($input: SearchInput!) {
            search(input: $input) {
                items { id name }
            }
        }
    """

class GraphQLClient(Client):
    @searchresource
    class Search:
        backend = BACKEND
        payload = PL(
            query=P(required=True),
            filter=P(type=PT.OBJECT)
        )
```

#### Algolia Search
```python
from clientfactory.decorators import algolia

@algolia
class BACKEND:
    appid = "YOUR_APP_ID"
    apikey = "YOUR_API_KEY"
    indices = ["primary_index", "secondary_index"]

class AlgoliaClient(Client):
    @searchresource
    class Search:
        backend = BACKEND
        payload = PL(
            query=P(required=True),
            page=P(default=1),
            hitsPerPage=P(default=20)
        )
```

### Comprehensive Auth Support

#### Basic Auth
```python
from clientfactory.auth import BasicAuth

client = Client(
    auth=BasicAuth(username="user", password="pass")
)
```

#### Bearer Token
```python
from clientfactory.auth import TokenAuth

client = Client(
    auth=TokenAuth.Bearer("my-token")
)
```

#### OAuth 2.0
```python
from clientfactory.auth import OAuthAuth

auth = OAuthAuth.ClientCredentials(
    clientid="id",
    clientsecret="secret",
    tokenurl="https://auth.example.com/token"
)
client = Client(auth=auth)
```

### Enhanced Session Management
```python
from clientfactory.session import EnhancedSession, Headers
from clientfactory.decorators import session

@session
class SESSION:
    headers = Headers(
        static={"User-Agent": "MyClient/1.0"},
        dynamic={
            "X-Timestamp": lambda: str(int(time.time()))
        }
    )
    persistcookies = True

client = Client(session=SESSION)
```

### Parameter Validation & Transformation
```python
from clientfactory.shorthands import PL, P, PT

PAYLOAD = PL(
    query=P(required=True),
    limit=P(type=PT.NUMBER, default=20),
    sort=P(choices=["asc", "desc"]),
    fields=P(type=PT.ARRAY, transform=lambda x: ",".join(x))
)
```

## Installation

```bash
pip install clientfactory
```

## Documentation

*under construction*

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
