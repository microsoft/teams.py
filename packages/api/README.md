> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams API Client

Core API client library for Microsoft Teams Bot Framework integration.
Provides HTTP clients, authentication, and typed models for Teams Bot Framework APIs.

## Features

- **API Clients**: Bot, User, Conversation, Team, and Meeting clients
- **Authentication**: ClientCredentials and TokenCredentials support
- **Activity Models**: Typed Pydantic models for Teams activities
- **JWT Tokens**: JsonWebToken implementation with TokenProtocol interface

## Authentication

```python
from microsoft.teams.api import ClientCredentials, TokenCredentials

# Client credentials authentication
credentials = ClientCredentials(
    client_id="your-app-id",
    client_secret="your-app-secret"
)

# Token-based authentication
credentials = TokenCredentials(
    client_id="your-app-id",
    token=your_token_function
)
```

## API Client Usage

```python
from microsoft.teams.api import ApiClient

# Initialize API client
api = ApiClient("https://smba.trafficmanager.net/amer/")

# Bot token operations
token_response = await api.bots.token.get(credentials)
graph_token = await api.bots.token.get_graph(credentials)

# User token operations
user_token = await api.users.token.get(params)
token_status = await api.users.token.get_status(params)
```

## Activity Models

```python
from microsoft.teams.api import MessageActivity, Activity, ActivityTypeAdapter

# Validate incoming activities
activity = ActivityTypeAdapter.validate_python(activity_data)

# Work with typed activities
if isinstance(activity, MessageActivity):
    print(f"Message: {activity.text}")
```
