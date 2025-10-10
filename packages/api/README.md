> [!CAUTION]
> This project is in public preview. We’ll do our best to maintain compatibility, but there may be breaking changes in upcoming releases. 

# Microsoft Teams API Client

<p>
    <a href="https://pypi.org/project/microsoft-teams-api/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-api" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-api/" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-api" />
    </a>
</p>

Core API client library for Microsoft Teams Bot Framework integration.
Provides HTTP clients, authentication, and typed models for Teams Bot Framework APIs.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>


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
