# ClientFactory

A Python framework for building API clients with minimal boilerplate while maintaining full configurability and extensibility.

## Features

- **Declarative API Definition**: Define your API structure using Python classes and decorators
- **Multiple Authentication Methods**: Built-in support for:
  - API Key authentication (header or query parameter)
  - OAuth 2.0 (client credentials, authorization code)
  - Session-based authentication with browser automation
  - Basic HTTP authentication
  - Token-based authentication
  - Custom authentication handlers
- **Resource Management**:
  - Organize endpoints into logical resource groups
  - Support for nested resources
  - Automatic URL construction
  - Path parameter handling
- **Request Processing**:
  - Pre-processing hooks for request modification
  - Post-processing hooks for response transformation
  - Automatic retries with configurable backoff
  - File upload support with progress tracking
- **Session Management**:
  - Persistent sessions with encryption
  - Cookie handling
  - Proxy support
  - Custom header management
- **Type Safety**: Full type hinting support for better IDE integration
- **Extensibility**: Every component is designed to be extended and customized

## Installation

```bash
pip install clientfactory
```

## Quick Start

### Basic Usage

```python
from clientfactory import Client, resource, get, post, ApiKeyAuth

class GitHub(Client):
    baseurl = "https://api.github.com"
    auth = ApiKeyAuth.header("your-token", "Authorization", prefix="Bearer")

    @resource
    class Repos:
        @get("user/repos")
        def list_repos(self): pass

        @post("user/repos")
        def create_repo(self, name: str, private: bool = False):
            return {"name": name, "private": private}

# Use the client
github = GitHub()
repos = github.repos.list_repos()
```

### Request Processing

```python
from clientfactory import Client, resource, get, preprocess, postprocess
from clientfactory.utils import Request, Response

class DataAPI(Client):
    baseurl = "https://api.example.com"

    @resource
    class Data:
        @preprocess
        def add_timestamp(self, request: Request) -> Request:
            """Add timestamp to all requests"""
            return request.WITH(
                headers={"X-Timestamp": str(time.time())}
            )

        @postprocess
        def extract_data(self, response: Response) -> dict:
            """Extract data field from response"""
            return response.json()["data"]

        @get("data/{id}")
        def get_data(self, id: str): pass
```

### File Uploads

```python
from clientfactory import Client, resource, post, UploadConfig
from clientfactory.utils import FileUpload

class Storage(Client):
    baseurl = "https://storage.example.com"

    @resource
    class Files:
        def progress(self, current: int, total: int):
            print(f"Uploaded {current}/{total} bytes")

        @post("upload")
        def upload(self, file: str):
            uploader = FileUpload(
                config=UploadConfig(
                    progresscallback=self.progress
                )
            )
            return uploader.multipart(
                url=self.url + "/upload",
                files={"file": file}
            )
```

### OAuth Authentication

```python
from clientfactory import Client, OAuth2Auth, resource, get

class ServiceAPI(Client):
    baseurl = "https://api.service.com"
    auth = OAuth2Auth.clientcredentials(
        clientid="your-client-id",
        clientsecret="your-client-secret",
        tokenurl="https://auth.service.com/token"
    )

    @resource
    class Users:
        @get("users/me")
        def me(self): pass
```

### Builder Pattern

```python
from clientfactory import ClientBuilder, ApiKeyAuth

# Create client programmatically
client = (ClientBuilder()
    .baseurl("https://api.example.com")
    .auth(ApiKeyAuth.header("your-key"))
    .sessioncfg(verify=False)  # Disable SSL verification
    .requestconfig(timeout=30.0)
    .headers({
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json"
    })
    .build())
```

### Session Persistence

```python
from clientfactory import Client, DiskPersist, PersistConfig

class WebApp(Client):
    baseurl = "https://webapp.example.com"

    def __init__(self):
        # Setup encrypted session persistence
        self.persist = DiskPersist(
            config=PersistConfig(
                path="~/.myapp/session",
                encrypt=True
            )
        )
        super().__init__()
```

## Advanced Usage

For more advanced usage examples, including:
- Custom authentication handlers
- Complex request/response processing
- Browser automation for web apps
- Request retries and backoff strategies
- Resource hierarchies
- Error handling

Visit our [Advanced Usage Guide](https://clientfactory.readthedocs.io/advanced/).

## Development

```bash
# Clone the repository
git clone https://github.com/schizoprada/clientfactory.git
cd clientfactory

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e ".[test,docs]"

# Run tests
pytest

# Build documentation
cd docs
make html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Support

- Documentation: [ReadTheDocs](https://clientfactory.readthedocs.io/)
- Issues: [GitHub Issues](https://github.com/schizoprada/clientfactory/issues)
- Discussions: [GitHub Discussions](https://github.com/schizoprada/clientfactory/discussions)
