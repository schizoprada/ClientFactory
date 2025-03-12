## Core Files

__init__.py
- Exposes main package interfaces (Client, ClientBuilder, decorators) and version info
- Handles package-level configuration and imports

client.py
- Implements core Client class that manages resources, auth, and session instances
- Provides high-level interface for making requests and configuring client behavior

builder.py
- Implements ClientBuilder for fluent/programmatic client configuration
- Constructs and validates Client instances with proper dependencies

## Auth Module

auth/base.py
- Defines BaseAuth abstract class with common authentication logic
- Provides interface for auth token management and request signing

auth/apikey.py
- Implements API key authentication using header or query parameter strategies
- Handles automatic key rotation and validation

auth/oauth.py
- Implements OAuth2 flows (client credentials, authorization code, etc.)
- Manages token refresh and storage

auth/session.py
- Implements cookie-based session authentication with form login
- Handles session maintenance and revalidation

## Resources Module

resources/base.py
- Defines BaseResource class for API endpoint representation and method handling
- Manages resource hierarchy and request/response processing

resources/decorators.py
- Implements @resource and HTTP method decorators (@get, @post, etc.)
- Handles method binding and configuration metadata

## Session Module

session/base.py
- Defines BaseSession with request/response lifecycle hooks
- Manages headers, cookies, and connection pooling

session/persistent.py
- Implements session persistence to disk with encryption
- Handles session restoration and validation

## Utils Module

utils/request.py
- Provides request preprocessing, validation, and transformation utilities
- Implements retry logic and error handling

utils/response.py
- Handles response parsing, data extraction, and error mapping
- Implements pagination and response streaming helpers

## Core Dependencies and Flow:

1. Client initialization:
   - Client → Auth → Session setup
   - Client → Resource registration
   - Client → Builder (optional)

2. Request flow:
   - Resource → Client → Auth → Session → Request
   - Response → Session → Client → Resource

3. Session management:
   - Session → Auth for token refresh
   - Session → Persistent for storage

4. Resource hierarchy:
   - Parent resources manage child resources
   - Resources use decorators for method configuration

5. Builder pattern:
   - Builder → Auth/Session/Resource configuration
   - Builder → Client instantiation


# ClientFactory Development Roadmap

## Phase 1: Core Request/Response Foundation
1. **utils/request.py & utils/response.py**
  - These are the most fundamental building blocks with minimal dependencies
  - Establishing request/response handling first gives us tools to build and test everything else
  - Includes retry logic, basic error handling, response parsing

2. **session/base.py**
  - Builds directly on request/response utilities
  - Provides the foundational HTTP client functionality
  - Must come before auth since authentication relies on session management

## Phase 2: Authentication Framework
3. **auth/base.py**
  - Depends on session functionality being in place
  - Required before implementing specific auth methods
  - Defines core interfaces other auth implementations will use

4. **auth/apikey.py**
  - Simplest auth implementation to test the base auth framework
  - Provides a basic working auth method for initial testing

## Phase 3: Resource Management
5. **resources/base.py**
  - Can now be built on working session and auth components
  - Required before implementing decorators
  - Defines how resources interact with client and handle requests

6. **resources/decorators.py**
  - Depends on resource base implementation
  - Enables the core declarative API design
  - Must be stable before building client class

## Phase 4: Client Implementation
7. **client.py**
  - Integrates all previous components
  - Provides the main user interface
  - Required before testing more complex features

8. **builder.py**
  - Depends on client implementation being stable
  - Provides alternative configuration approach
  - Helps validate component integration

## Phase 5: Advanced Features
9. **auth/oauth.py & auth/session.py**
  - More complex auth implementations
  - Build on stable core auth framework
  - Can be properly tested with working client

10. **session/persistent.py**
    - Adds advanced session features
    - Requires stable session base implementation
    - Not critical for core functionality

## Phase 6: Package Configuration
11. **__init__.py**
    - Exposes public interfaces
    - Requires all components to be stable
    - Finalizes the user-facing API

## Testing Strategy
- Each phase includes:
  1. Unit tests for new components
  2. Integration tests with existing components
  3. Example implementations
  4. Documentation updates

## Development Guidelines
1. Each component should be testable in isolation
2. Public interfaces should be stable before moving to dependent components
3. Documentation should be written alongside code
4. Example implementations should be created for each major feature
5. Breaking changes should only occur within the same phase

## Key Milestones
1. First working request (Phase 1)
2. First authenticated request (Phase 2)
3. First declarative resource definition (Phase 3)
4. First complete client implementation (Phase 4)
5. First OAuth flow (Phase 5)
6. First public release (Phase 6)
