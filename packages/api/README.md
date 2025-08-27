> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams API Client

Core API client functionality with models and clients for Microsoft Teams integration.
Provides HTTP abstraction, authentication, and typed models for Teams Bot Framework APIs.

## Features

- **Bot Framework Integration**: Complete client library for Teams Bot Framework APIs
- **Authentication System**: Support for ClientCredentials and TokenCredentials
- **Token Management**: JsonWebToken implementation with TokenProtocol interface
- **Multi-tenant Support**: Tenant-specific token caching and management
- **Type Safety**: Comprehensive Pydantic models for all API interactions
- **HTTP Abstraction**: Robust HTTP client with interceptors and middleware support

## Authentication Types

### ClientCredentials

For application authentication using client ID and secret:

```python
from microsoft.teams.api import ClientCredentials

credentials = ClientCredentials(
    client_id="your-app-id",
    client_secret="your-app-secret",
    tenant_id="optional-tenant-id"  # For single-tenant apps
)
```

### TokenCredentials

For external authentication providers:

```python
from microsoft.teams.api import TokenCredentials

credentials = TokenCredentials(
    client_id="your-app-id",
    tenant_id="tenant-id",
    token=your_token_function  # Callable that returns access token
)
```

## Token Protocol

The package implements `TokenProtocol` for unified token handling:

```python
from microsoft.teams.api import JsonWebToken, TokenProtocol

# Create token from JWT string
token: TokenProtocol = JsonWebToken("jwt-token-string")

# Access token properties
print(f"App ID: {token.app_id}")
print(f"Expires: {token.expiration}")
print(f"From: {token.from_}")

# Convert back to string
jwt_string = str(token)
```

## API Clients

### Bot Token Client

Manages bot authentication tokens:

```python
from microsoft.teams.api import ApiClient

api = ApiClient()
token_response = await api.bots.token.get(credentials)
graph_token = await api.bots.token.get_graph(credentials)
```

### User Token Client

Handles user authentication and token exchange:

```python
user_token = await api.users.token.get(params)
aad_tokens = await api.users.token.get_aad(params)
```

## Multi-tenant Support

The API client supports multi-tenant applications with automatic tenant token caching:

- Tenant-specific credentials creation
- Automatic token caching per tenant
- Proper token lifecycle management
- Type-safe tenant ID handling
