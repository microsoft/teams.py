> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams App Framework

High-level framework for building Microsoft Teams bots and applications.
Handles routing, middleware, events, and provides OAuth integration for Teams apps.

## Features

- **Activity Routing**: Flexible routing system for handling different activity types
- **Middleware Support**: Extensible middleware chain for request processing
- **OAuth Integration**: Built-in OAuth flow handling for user authentication
- **Microsoft Graph Integration**: Direct access to Graph APIs through `user_graph` and `app_graph` properties
- **Plugin System**: Extensible plugin architecture for adding functionality
- **Event Handling**: Comprehensive event system for application lifecycle management

## Graph Clients

The framework provides seamless Microsoft Graph integration through two client types:

### User Graph Client (`ctx.user_graph`)

Authenticated with the signed-in user's token for user-specific operations:

```python
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if ctx.is_signed_in:
        # User is signed in, now we can safely access user_graph
        if ctx.user_graph:
            me = await ctx.user_graph.me.get()
            await ctx.send(f"Hello {me.display_name}!")
    else:
        # User needs to sign in first
        await ctx.sign_in()
```

### App Graph Client (`ctx.app_graph`)

Authenticated with the application's token for app-only operations:

```python
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if ctx.app_graph:
        # App-only operations
        app_info = await ctx.app_graph.applications.by_application_id("app-id").get()
        await ctx.send(f"App: {app_info.display_name}")
```

Both clients are lazily initialized and automatically handle authentication through the framework's token management system.

## Optional Graph Dependencies

Microsoft Graph functionality is optional and requires additional dependencies. To enable Graph integration:

```bash
# Install with Graph support
pip install microsoft-teams-apps[graph]
```

If Graph dependencies are not installed, the `user_graph` and `app_graph` properties will return `None`, allowing your application to gracefully handle the absence of Graph functionality.

```python
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    if ctx.app_graph:
        # Graph is available - use it
        app_info = await ctx.app_graph.applications.by_application_id("app-id").get()
        await ctx.send(f"App: {app_info.display_name}")
    else:
        # Graph not available - provide alternative functionality
        await ctx.send("Graph functionality not available")
```

## Advanced Token Management

For advanced scenarios, you can configure custom token management with enhanced security features:

### Multi-Tenant Security

When working with static tokens in multi-tenant applications, you can restrict tokens to specific tenants to prevent cross-tenant data leakage:

```python
from microsoft.teams.apps.graph_token_manager import GraphTokenManager
from microsoft.teams.api import JsonWebToken

# Secure: Restrict static token to specific tenant
safe_token = JsonWebToken("your-token-here")
manager = GraphTokenManager.create_with_static_token(
    token=safe_token,
    allowed_tenant_id="tenant-123"  # Security: Only works for this tenant
)

# This will work
token = await manager.get_token("tenant-123")

# This will raise ValueError - prevents accidental cross-tenant access
token = await manager.get_token("tenant-456")  # ❌ Security error
```

### Dynamic Token Refresh

For applications requiring dynamic token management across multiple tenants:

```python
async def refresh_tenant_token(tenant_id: Optional[str]) -> Optional[str]:
    """Custom token refresh logic for different tenants."""
    if tenant_id == "tenant-a":
        return await get_tenant_a_token()
    elif tenant_id == "tenant-b":
        return await get_tenant_b_token()
    return None

# Dynamic token management with automatic refresh
manager = GraphTokenManager.create_with_callback(
    refresh_callback=refresh_tenant_token,
    logger=app.logger
)
```

### Security Best Practices

- **Always specify `allowed_tenant_id` for production static tokens**
- **Use callback-based providers for multi-tenant applications**  
- **Validate token scope matches intended operations**
- **Monitor token usage in logs for security auditing**
