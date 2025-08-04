# Teams OAuth with Microsoft Graph Integration

This is a Python Teams application that demonstrates OAuth authentication and Microsoft Graph API integration using the Teams AI Python SDK.

## Features

- **OAuth Authentication** - Users can sign in with their Microsoft 365 account
- **Microsoft Graph Integration** - Access user profile and Teams data via Graph APIs
- **Interactive Testing** - Commands to test different Graph API endpoints
- **Comprehensive Error Handling** - Clear guidance for permission issues

## Prerequisites

- Python 3.12 or higher
- Azure App Registration with proper permissions
- Teams Developer Portal app configuration

## Quick Start

### 1. Install Dependencies

```bash
cd tests/oauth
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the `tests/oauth/src/` directory:

```env
CLIENT_ID=your_azure_app_client_id
CLIENT_SECRET=your_azure_app_client_secret
TENANT_ID=your_azure_tenant_id
```

### 3. Run the Application

```bash
cd tests/oauth/src
python main.py
```

## Testing Graph Integration

Once the app is running and users are signed in, they can test Graph functionality:

- **Type `graph`** - Test user profile retrieval
- **Type `teams`** - Test Teams data access with scope validation
- **Type `signout`** - Sign out the current user
- **Any other message** - Show help menu

## Azure App Registration Setup

### Required Graph API Permissions

Add these **Delegated** permissions in your Azure App Registration:

1. **Microsoft Graph**:
   - `User.Read` - Read user profile (required)
   - `User.ReadBasic.All` - Read basic profiles of all users
   - `Team.ReadBasic.All` - Read basic team information
   - `offline_access` - Maintain access to data

### OAuth Connection Configuration

In your Teams app OAuth settings, configure these scopes:

```
User.Read User.ReadBasic.All Team.ReadBasic.All offline_access
```

### Admin Consent

**Important**: After adding permissions, click "Grant admin consent" in the Azure Portal.

## Troubleshooting

### Common Issues

**403 Forbidden Errors**
- Verify all required permissions are granted in Azure Portal
- Ensure admin consent has been provided
- Check that OAuth connection requests the correct scopes
- Users may need to sign out and sign in again to get new permissions

**Token Not Available**
- Ensure user is signed in before accessing Graph APIs
- Check that `default_connection_name` is set to "graph" in the app configuration
- Verify OAuth connection is properly configured

### Debug Information

The application provides detailed logging when Graph API calls fail, including:
- Current token scopes
- Required permissions for specific operations
- Step-by-step setup instructions for Azure Portal

## Graph Integration Code

The Graph integration is powered by the `microsoft-teams-graph` package. Key implementation details:

```python
from microsoft.teams.graph import enable_graph_integration

# Enable Graph integration
enable_graph_integration()

# Access Graph client in message handlers
graph_client = await ctx.get_graph_client()
if graph_client:
    user_info = await graph_client.get_me()
    teams_info = await graph_client.get_my_teams()
```

For more details, see the Graph package documentation in `/packages/graph/README.md`.
