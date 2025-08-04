# Microsoft Teams Graph SDK Integration

The `microsoft-teams-graph` package provides seamless integration between the Teams AI Python SDK and Microsoft Graph APIs. It enables Teams applications to access Graph data with automatic OAuth token handling and zero-configuration setup.

## Features

- **Zero-configuration setup** - Automatically uses Teams OAuth tokens
- **Type-safe Graph client** - Fully typed Python interface to Graph APIs
- **Comprehensive error handling** - Detailed permission error guidance
- **Debug-friendly** - Built-in logging and scope validation
- **Production ready** - Handles token refresh and error scenarios

## Installation

```bash
pip install microsoft-teams-graph
```

Or with the full Teams SDK:

```bash
pip install microsoft-teams[graph]
```

## Quick Start

### 1. Enable Graph Integration

```python
from microsoft.teams.app import App
from microsoft.teams.graph import enable_graph_integration

app = App()

# Enable Graph integration - adds get_graph_client() method to ActivityContext
enable_graph_integration()

@app.on_message
async def handle_message(ctx):
    if ctx.is_signed_in:
        # Get authenticated Graph client
        graph_client = await ctx.get_graph_client()
        if graph_client:
            # Access Graph APIs
            user_info = await graph_client.get_me()
            await ctx.send(f"Hello {user_info.get('displayName', 'User')}!")
```

### 2. Configure OAuth Scopes

The package automatically requests these default scopes:
- `User.Read` - Basic user profile
- `User.ReadBasic.All` - Basic info for all users
- `Team.ReadBasic.All` - Basic team information
- `offline_access` - Token refresh capability

To customize scopes:

```python
# Request additional scopes
enable_graph_integration(scopes=[
    "User.Read",
    "User.ReadBasic.All", 
    "Team.ReadBasic.All",
    "Calendars.Read",
    "Files.Read",
    "offline_access"
])
```

## Available Graph Operations

### User Information
```python
graph_client = await ctx.get_graph_client()

# Get current user
user = await graph_client.get_me()
print(f"User: {user.get('displayName')}")
```

### Teams Information
```python
# Get user's teams
teams = await graph_client.get_my_teams()
teams_list = teams.get('value', [])
print(f"User is member of {len(teams_list)} teams")

# Get specific team details
team_info = await graph_client.get_team(team_id)
print(f"Team: {team_info.get('displayName')}")

# Get team channels
channels = await graph_client.get_team_channels(team_id)
channels_list = channels.get('value', [])
```

### Token Scope Validation
```python
# Check what permissions the current token has
await graph_client.check_token_scopes()
```

## Error Handling

The package provides comprehensive error handling with actionable guidance:

```python
try:
    teams = await graph_client.get_my_teams()
except Exception as e:
    if "403" in str(e) or "Forbidden" in str(e):
        # Detailed permission error guidance is automatically logged
        await ctx.send("L Missing Graph permissions. Check console for setup instructions.")
    else:
        await ctx.send(f"Graph API error: {e}")
```

## Azure App Registration Setup

To use Graph integration, your Azure App Registration needs:

### Required API Permissions
Add these **Delegated** permissions in Azure Portal:

1. **Microsoft Graph**:
   - `User.Read` - Sign in and read user profile
   - `User.ReadBasic.All` - Read basic profiles of all users  
   - `Team.ReadBasic.All` - Read basic team information
   - `offline_access` - Maintain access to data

### OAuth Connection Configuration
In your Teams app OAuth settings:

```json
{
  "scopes": "User.Read User.ReadBasic.All Team.ReadBasic.All offline_access"
}
```

### Admin Consent
**Important**: Click "Grant admin consent" in Azure Portal after adding permissions.

## Troubleshooting

### Common Issues

**403 Forbidden Errors**
- Verify permissions are granted in Azure Portal
- Ensure admin consent is provided
- Check that OAuth connection requests correct scopes
- Users may need to sign out and sign in again

**Token Not Available**
- Ensure user is signed in: `ctx.is_signed_in`
- Check OAuth connection configuration
- Verify `default_connection_name` is set correctly

**Import Errors**
- Install required dependencies: `pip install azure-identity msgraph-sdk`
- Ensure `microsoft-teams-app` is installed

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# The package will log detailed information about:
# - Requested vs actual token scopes
# - Graph API call details  
# - Permission errors with setup guidance
```

## API Reference

### `enable_graph_integration(scopes=None)`
Enables Graph integration by adding `get_graph_client()` method to `ActivityContext`.

**Parameters:**
- `scopes` (list, optional): Graph API scopes to request

### `GraphClient` Methods
- `get_me()` ’ `Dict[str, Any]` - Get current user information
- `get_my_teams()` ’ `Dict[str, Any]` - Get user's teams
- `get_team(team_id)` ’ `Dict[str, Any]` - Get team details  
- `get_team_channels(team_id)` ’ `Dict[str, Any]` - Get team channels
- `check_token_scopes()` ’ `None` - Validate token permissions

## Examples

See the `/tests/oauth/` directory for a complete working example of Graph integration in a Teams application.

## Contributing

This package is part of the Teams AI Python SDK. Please see the main repository for contribution guidelines.

## License

Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.