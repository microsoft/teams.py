# Constants Audit for microsoft-teams-apps

This document provides a comprehensive audit of all hardcoded constants in the `microsoft-teams-apps` package and proposes a Config object design to make these values user-configurable.

## 1. Current Constants Inventory

### 1.1 URL/Endpoint Constants

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| Bot API Base URL | `https://smba.trafficmanager.net/teams` | `app.py:100` | Base URL for Bot Framework API client |
| Bot Framework Issuer | `https://api.botframework.com` | `token_validator.py:64` | Valid issuer for Bot Framework service tokens |
| Bot Framework JWKS URI | `https://login.botframework.com/v1/.well-known/keys` | `token_validator.py:66` | JWKS endpoint for Bot Framework token validation |
| Entra ID Issuer | `https://login.microsoftonline.com/{tenant_id}/v2.0` | `token_validator.py:87` | Valid issuer for Entra ID tokens |
| Entra ID JWKS URI | `https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys` | `token_validator.py:92` | JWKS endpoint for Entra ID token validation |
| Activity Endpoint Path | `/api/messages` | `http_plugin.py:111,340` | HTTP endpoint path for receiving activities |
| Health Check Path | `/` | `http_plugin.py:346` | HTTP endpoint for health checks |

### 1.2 Network Configuration

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| Default Port | `3978` | `app.py:219` | Default HTTP server port (from PORT env var or fallback) |
| Server Host | `0.0.0.0` | `http_plugin.py:152` | HTTP server bind address |
| User-Agent | `teams.py[app]/{version}` | `app.py:61` | HTTP User-Agent header value |
| Uvicorn Log Level | `info` | `http_plugin.py:152` | Default log level for uvicorn server |

### 1.3 Authentication & Security

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| JWT Leeway Seconds | `300` (5 minutes) | `token_validator.py:13` | Clock skew tolerance for JWT validation |
| Default Tenant ID | `botframework.com` | `graph_token_manager.py:37` | Default tenant for Graph API tokens |
| Skip Auth | `False` | `options.py:40` | Whether to skip authentication |
| Default Connection Name | `graph` | `options.py:42,80` | Default OAuth connection name |

### 1.4 Retry Configuration

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| Max Retry Attempts | `5` | `retry.py:22` | Maximum number of retry attempts |
| Initial Retry Delay | `0.5` seconds | `retry.py:23` | Initial delay before first retry |
| Max Retry Delay | `30.0` seconds | `retry.py:24` | Maximum cap for retry delay |
| Default Jitter Type | `full` | `retry.py:25` | Default jitter strategy (none/full/equal/decorrelated) |

### 1.5 Sign-In Configuration

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| OAuth Card Text | `Please Sign In...` | `activity_context.py:67` | Default text for OAuth card |
| Sign-In Button Text | `Sign In` | `activity_context.py:68` | Default text for sign-in button |

### 1.6 Logger Names

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| App Logger | `@teams/app` | `app.py:74` | Main application logger name |
| HTTP Plugin Logger | `@teams/http-plugin` | `http_plugin.py:75` | HTTP plugin logger name |
| Token Validator Logger | `@teams/token-validator` | `token_validator.py:46` | Token validator logger name |
| HTTP Stream Logger | `@teams/http-stream` | `http_stream.py` | HTTP stream logger name |
| Retry Logger | `@teams/retry` | `retry.py:39` | Retry utility logger name |

### 1.7 Plugin System

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| Plugin Metadata Key | `teams:plugin` | `metadata.py:11` | Attribute name for plugin metadata |

## 2. Proposed Config Object Design

### 2.1 Design Principles

1. **Backward Compatibility**: Existing code should work without changes
2. **User Customization**: All constants should be easily overridable
3. **Type Safety**: Use TypedDict/dataclass for strong typing
4. **Sensible Defaults**: Maintain current behavior by default
5. **Hierarchical Structure**: Group related settings logically
6. **Environment Variables**: Support env var overrides where appropriate

### 2.2 Proposed Structure

```python
from dataclasses import dataclass, field
from typing import Optional, Literal

JitterType = Literal["none", "full", "equal", "decorrelated"]

@dataclass
class NetworkConfig:
    """Network and HTTP server configuration."""
    
    default_port: int = 3978
    """Default port for HTTP server (overridden by PORT env var)"""
    
    host: str = "0.0.0.0"
    """Server bind address"""
    
    user_agent: Optional[str] = None
    """Custom User-Agent header (defaults to teams.py[app]/{version})"""
    
    uvicorn_log_level: str = "info"
    """Log level for uvicorn server"""


@dataclass
class EndpointConfig:
    """API endpoint URLs and paths."""
    
    bot_api_base_url: str = "https://smba.trafficmanager.net/teams"
    """Base URL for Bot Framework API"""
    
    activity_path: str = "/api/messages"
    """HTTP endpoint path for receiving activities"""
    
    health_check_path: str = "/"
    """HTTP endpoint for health checks"""


@dataclass
class AuthConfig:
    """Authentication and security configuration."""
    
    jwt_leeway_seconds: int = 300
    """Clock skew tolerance for JWT validation (seconds)"""
    
    bot_framework_issuer: str = "https://api.botframework.com"
    """Valid issuer for Bot Framework service tokens"""
    
    bot_framework_jwks_uri: str = "https://login.botframework.com/v1/.well-known/keys"
    """JWKS endpoint for Bot Framework token validation"""
    
    entra_id_issuer_template: str = "https://login.microsoftonline.com/{tenant_id}/v2.0"
    """Template for Entra ID issuer URL"""
    
    entra_id_jwks_uri_template: str = "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    """Template for Entra ID JWKS endpoint"""
    
    default_graph_tenant_id: str = "botframework.com"
    """Default tenant ID for Graph API tokens"""


@dataclass
class RetryConfig:
    """Retry behavior configuration."""
    
    max_attempts: int = 5
    """Maximum number of retry attempts"""
    
    initial_delay: float = 0.5
    """Initial delay before first retry (seconds)"""
    
    max_delay: float = 30.0
    """Maximum cap for retry delay (seconds)"""
    
    jitter_type: JitterType = "full"
    """Jitter strategy: none, full, equal, or decorrelated"""


@dataclass
class SignInConfig:
    """Sign-in UI configuration."""
    
    oauth_card_text: str = "Please Sign In..."
    """Default text for OAuth card"""
    
    sign_in_button_text: str = "Sign In"
    """Default text for sign-in button"""


@dataclass
class LoggerConfig:
    """Logger name configuration."""
    
    app_logger_name: str = "@teams/app"
    """Main application logger name"""
    
    http_plugin_logger_name: str = "@teams/http-plugin"
    """HTTP plugin logger name"""
    
    token_validator_logger_name: str = "@teams/token-validator"
    """Token validator logger name"""
    
    http_stream_logger_name: str = "@teams/http-stream"
    """HTTP stream logger name"""
    
    retry_logger_name: str = "@teams/retry"
    """Retry utility logger name"""


@dataclass
class PluginConfig:
    """Plugin system configuration."""
    
    metadata_key: str = "teams:plugin"
    """Attribute name for plugin metadata"""


@dataclass
class AppConfig:
    """
    Centralized configuration for Teams application.
    
    All hardcoded constants are now configurable through this object.
    Users can customize behavior by passing a custom AppConfig to the App.
    
    Example:
        ```python
        from microsoft.teams.apps import App, AppConfig, NetworkConfig
        
        # Customize network settings
        config = AppConfig(
            network=NetworkConfig(
                default_port=5000,
                user_agent="MyCustomBot/1.0"
            )
        )
        
        app = App(config=config)
        ```
    """
    
    network: NetworkConfig = field(default_factory=NetworkConfig)
    """Network and HTTP server settings"""
    
    endpoints: EndpointConfig = field(default_factory=EndpointConfig)
    """API endpoint URLs and paths"""
    
    auth: AuthConfig = field(default_factory=AuthConfig)
    """Authentication and security settings"""
    
    retry: RetryConfig = field(default_factory=RetryConfig)
    """Retry behavior settings"""
    
    signin: SignInConfig = field(default_factory=SignInConfig)
    """Sign-in UI settings"""
    
    logger: LoggerConfig = field(default_factory=LoggerConfig)
    """Logger name settings"""
    
    plugin: PluginConfig = field(default_factory=PluginConfig)
    """Plugin system settings"""
```

### 2.3 Integration Approach

#### Phase 1: Create Config Module
- Create `packages/apps/src/microsoft/teams/apps/config.py` with all config classes
- Export from `__init__.py`

#### Phase 2: Update App Class
- Add optional `config: Optional[AppConfig] = None` parameter to `App.__init__()`
- Store config as `self.config = config or AppConfig()`
- Pass config to components that need it

#### Phase 3: Update Components
- Update `app.py` to use `self.config.network.*` and `self.config.endpoints.*`
- Update `http_plugin.py` to accept and use config
- Update `token_validator.py` to use `config.auth.*`
- Update `retry.py` to use `config.retry.*`
- Update `activity_context.py` to use `config.signin.*`
- Update logger creation to use `config.logger.*`

#### Phase 4: Maintain Backward Compatibility
- Keep existing environment variable support (PORT, etc.)
- Ensure default behavior unchanged
- Environment variables take precedence over config defaults

#### Phase 5: Documentation & Tests
- Add comprehensive examples to README
- Create tests for config customization
- Document all config options

## 3. Benefits

1. **User Control**: Users can customize all aspects of the framework without modifying source code
2. **Testing**: Easier to create test configurations (e.g., custom ports, mock URLs)
3. **Multi-Environment**: Different configurations for dev/staging/production
4. **Discovery**: All configurable options in one place
5. **Type Safety**: IDE autocomplete and type checking for all options
6. **Documentation**: Self-documenting through dataclass fields and docstrings

## 4. Migration Path

### For End Users
```python
# Before (implicit defaults)
app = App(client_id="...", client_secret="...")

# After (explicit config, but backward compatible)
app = App(client_id="...", client_secret="...")

# After (with customization)
config = AppConfig(
    network=NetworkConfig(default_port=5000),
    auth=AuthConfig(jwt_leeway_seconds=600)
)
app = App(client_id="...", client_secret="...", config=config)
```

### For Framework Developers
```python
# Before
USER_AGENT = f"teams.py[app]/{version}"
port = int(os.getenv("PORT", "3978"))

# After
user_agent = self.config.network.user_agent or f"teams.py[app]/{version}"
port = int(os.getenv("PORT", str(self.config.network.default_port)))
```

## 5. Future Enhancements

1. **Config File Support**: Load from YAML/JSON/TOML files
2. **Environment Variable Mapping**: Auto-map config fields to env vars
3. **Validation**: Add validators for config values (e.g., port ranges)
4. **Profiles**: Pre-built configs for common scenarios (local dev, Azure, etc.)
5. **Runtime Updates**: Allow some config values to be updated at runtime
