# Microsoft Teams Graph Integration

<p>
    <a href="https://pypi.org/project/microsoft-teams-graph" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-graph" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-graph" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-graph" />
    </a>
</p>

This package provides seamless access to Microsoft Graph APIs from Teams bots and agents built with the Microsoft Teams AI SDK for Python.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Key Features

- **Token Integration**: Unified token handling using the Token type from microsoft-teams-common
- **Flexible Token Sources**: Supports strings, StringLike objects, callables, async callables, or None
- **Automatic Token Resolution**: Leverages common resolve_token utility for consistent handling

## Requirements

- Teams AI Library for Python
- Microsoft Graph SDK for Python (msgraph-sdk)
- Azure Core library (azure-core)
- Microsoft Teams Common library (microsoft-teams-common)

## Quick Start

### Basic Usage with Teams Bot

```python
from microsoft.teams.graph import get_graph_client
from microsoft.teams.apps import App, ActivityContext
from microsoft.teams.api import MessageActivity

app = App()

@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if not ctx.is_signed_in:
        await ctx.sign_in()
        return

    # Create Graph client using user's token
    graph = get_graph_client(ctx.user_token)

    # Get user profile
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}!")

    # Get user's Teams
    teams = await graph.me.joined_teams.get()
    if teams and teams.value:
        team_names = [team.display_name for team in teams.value]
        await ctx.send(f"You're in {len(team_names)} teams: {', '.join(team_names)}")
```

### Token Integration

```python
from microsoft.teams.common.http.client_token import Token

def create_token_callable(ctx: ActivityContext) -> Token:
    """Create a callable token that refreshes automatically."""
    def get_fresh_token():
        # This is called on each Graph API request
        return ctx.user_token  # Always returns current valid token

    return get_fresh_token

# Use with Graph client
graph = get_graph_client(create_token_callable(ctx))
```

        await ctx.sign_in()
        return

    # Use the user token that's already available in the context
    graph = get_graph_client(ctx.user_token)

    # Make Graph API calls
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}!")

    # Make Graph API calls
    me = await graph.me.get()
    await ctx.send(f"Hello {me.display_name}!")

````

## Token Type Usage

The package uses the Token type from microsoft-teams-common for flexible token handling. You can provide tokens in several formats:

### String Token (Simplest)

```python
# Direct string token
graph = get_graph_client("eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...")
````

### Callable Token (Dynamic)

```python
def get_token():
    """Callable that returns a string token."""
    # Get your access token from wherever (Teams API, cache, etc.)
    return get_access_token_from_somewhere()

# Use the callable with get_graph_client
graph = get_graph_client(get_token)
```

### Async Callable Token

```python
async def get_token_async():
    """Async callable that returns a string token."""
    # Fetch token asynchronously
    token_response = await some_api_call()
    return token_response.access_token

graph = get_graph_client(get_token_async)
```

### Dynamic Token Retrieval

```python
def get_fresh_token():
    """Callable that fetches a fresh token on each invocation."""
    # This will be called each time the Graph client needs a token
    fresh_token = fetch_latest_token_from_api()
    return fresh_token

graph = get_graph_client(get_fresh_token)
```

## Authentication

The package uses Token-based authentication with automatic resolution through the common library. Teams tokens are pre-authorized through the OAuth connection configured in your Azure Bot registration.

## API Usage Examples

```python
# Get user profile
me = await graph.me.get()

# Get recent emails with specific fields
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder

query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
    select=["subject", "from", "receivedDateTime"],
    top=5
)
request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
    query_parameters=query_params
)
messages = await graph.me.messages.get(request_configuration=request_config)
```
