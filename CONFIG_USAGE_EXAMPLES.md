# AppConfig Usage Examples

This document provides examples of how to use the `AppConfig` object to customize your Teams application.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Network Configuration](#network-configuration)
- [Authentication Configuration](#authentication-configuration)
- [Retry Configuration](#retry-configuration)
- [Sign-In Customization](#sign-in-customization)
- [Logger Configuration](#logger-configuration)
- [Complete Example](#complete-example)
- [Environment-Specific Configurations](#environment-specific-configurations)

## Basic Usage

### Using Default Configuration

The simplest way to use the app is with all default values:

```python
from microsoft.teams.apps import App

# Uses all default configuration values
app = App(
    client_id="your-client-id",
    client_secret="your-client-secret",
    tenant_id="your-tenant-id"
)
```

### Creating a Custom Config

To customize configuration, create an `AppConfig` object:

```python
from microsoft.teams.apps import App, AppConfig, NetworkConfig

# Customize just the network settings
config = AppConfig(
    network=NetworkConfig(default_port=5000)
)

app = App(
    client_id="your-client-id",
    client_secret="your-client-secret",
    tenant_id="your-tenant-id",
    config=config
)
```

## Network Configuration

### Change Default Port

```python
from microsoft.teams.apps import AppConfig, NetworkConfig

config = AppConfig(
    network=NetworkConfig(
        default_port=8080  # Use port 8080 instead of default 3978
    )
)
```

### Customize User Agent

```python
from microsoft.teams.apps import AppConfig, NetworkConfig

config = AppConfig(
    network=NetworkConfig(
        user_agent="MyCustomBot/2.0 (contact@example.com)"
    )
)
```

### Change Server Host

```python
from microsoft.teams.apps import AppConfig, NetworkConfig

config = AppConfig(
    network=NetworkConfig(
        host="127.0.0.1"  # Only bind to localhost
    )
)
```

### Adjust Uvicorn Log Level

```python
from microsoft.teams.apps import AppConfig, NetworkConfig

config = AppConfig(
    network=NetworkConfig(
        uvicorn_log_level="debug"  # More verbose logging
    )
)
```

## Authentication Configuration

### Increase JWT Leeway

```python
from microsoft.teams.apps import AppConfig, AuthConfig

# Allow 10 minutes of clock skew (useful for development)
config = AppConfig(
    auth=AuthConfig(
        jwt_leeway_seconds=600
    )
)
```

### Custom Bot Framework URLs (for testing)

```python
from microsoft.teams.apps import AppConfig, AuthConfig

config = AppConfig(
    auth=AuthConfig(
        bot_framework_issuer="https://test.botframework.com",
        bot_framework_jwks_uri="https://test.botframework.com/keys"
    )
)
```

### Custom Graph Tenant ID

```python
from microsoft.teams.apps import AppConfig, AuthConfig

config = AppConfig(
    auth=AuthConfig(
        default_graph_tenant_id="your-tenant-id.onmicrosoft.com"
    )
)
```

## Retry Configuration

### Aggressive Retry Strategy

```python
from microsoft.teams.apps import AppConfig, RetryConfig

# Try more times with longer delays
config = AppConfig(
    retry=RetryConfig(
        max_attempts=10,
        initial_delay=1.0,
        max_delay=60.0,
        jitter_type="decorrelated"
    )
)
```

### Conservative Retry Strategy

```python
from microsoft.teams.apps import AppConfig, RetryConfig

# Fail fast with minimal retries
config = AppConfig(
    retry=RetryConfig(
        max_attempts=2,
        initial_delay=0.1,
        max_delay=5.0,
        jitter_type="none"
    )
)
```

### Production Retry Strategy

```python
from microsoft.teams.apps import AppConfig, RetryConfig

# Balanced approach for production
config = AppConfig(
    retry=RetryConfig(
        max_attempts=5,
        initial_delay=0.5,
        max_delay=30.0,
        jitter_type="equal"  # Prevents thundering herd
    )
)
```

## Sign-In Customization

### Custom Sign-In Messages

```python
from microsoft.teams.apps import AppConfig, SignInConfig

config = AppConfig(
    signin=SignInConfig(
        oauth_card_text="Authentication Required - Please log in to continue",
        sign_in_button_text="Login with Microsoft"
    )
)
```

### Localized Sign-In Text

```python
from microsoft.teams.apps import AppConfig, SignInConfig

# Spanish localization
config = AppConfig(
    signin=SignInConfig(
        oauth_card_text="Por favor inicie sesión...",
        sign_in_button_text="Iniciar Sesión"
    )
)
```

## Logger Configuration

### Custom Logger Names

```python
from microsoft.teams.apps import AppConfig, LoggerConfig

config = AppConfig(
    logger=LoggerConfig(
        app_logger_name="mycompany/teams-bot",
        http_plugin_logger_name="mycompany/http",
        retry_logger_name="mycompany/retry"
    )
)
```

## Complete Example

### Production Configuration

```python
from microsoft.teams.apps import (
    App,
    AppConfig,
    NetworkConfig,
    EndpointConfig,
    AuthConfig,
    RetryConfig,
    SignInConfig,
    LoggerConfig
)

# Create a comprehensive production config
production_config = AppConfig(
    network=NetworkConfig(
        default_port=8080,
        host="0.0.0.0",
        user_agent="MyTeamsBot/1.0 Production",
        uvicorn_log_level="info"
    ),
    endpoints=EndpointConfig(
        bot_api_base_url="https://smba.trafficmanager.net/teams",
        activity_path="/api/messages",
        health_check_path="/health"
    ),
    auth=AuthConfig(
        jwt_leeway_seconds=300,
        default_graph_tenant_id="mycompany.onmicrosoft.com"
    ),
    retry=RetryConfig(
        max_attempts=5,
        initial_delay=0.5,
        max_delay=30.0,
        jitter_type="equal"
    ),
    signin=SignInConfig(
        oauth_card_text="Please sign in to access company resources",
        sign_in_button_text="Sign In with Microsoft"
    ),
    logger=LoggerConfig(
        app_logger_name="mycompany/bot",
        http_plugin_logger_name="mycompany/http",
        token_validator_logger_name="mycompany/auth"
    )
)

# Create app with production config
app = App(
    client_id="your-prod-client-id",
    client_secret="your-prod-client-secret",
    tenant_id="your-tenant-id",
    config=production_config
)
```

### Development Configuration

```python
from microsoft.teams.apps import App, AppConfig, NetworkConfig, AuthConfig, LoggerConfig

# Development-friendly configuration
dev_config = AppConfig(
    network=NetworkConfig(
        default_port=3978,
        host="127.0.0.1",  # Only accessible locally
        uvicorn_log_level="debug"  # Verbose logging
    ),
    auth=AuthConfig(
        jwt_leeway_seconds=600  # More forgiving for clock skew
    ),
    logger=LoggerConfig(
        app_logger_name="dev/bot",
        http_plugin_logger_name="dev/http"
    )
)

app = App(
    client_id="your-dev-client-id",
    client_secret="your-dev-client-secret",
    tenant_id="your-tenant-id",
    config=dev_config
)
```

## Environment-Specific Configurations

### Configuration Factory Pattern

```python
from microsoft.teams.apps import AppConfig, NetworkConfig, AuthConfig, LoggerConfig
import os

def get_config(environment: str) -> AppConfig:
    """Get configuration based on environment."""
    
    if environment == "production":
        return AppConfig(
            network=NetworkConfig(
                default_port=8080,
                uvicorn_log_level="warning"
            ),
            auth=AuthConfig(
                jwt_leeway_seconds=300
            )
        )
    
    elif environment == "staging":
        return AppConfig(
            network=NetworkConfig(
                default_port=8080,
                uvicorn_log_level="info"
            ),
            auth=AuthConfig(
                jwt_leeway_seconds=300
            ),
            logger=LoggerConfig(
                app_logger_name="staging/bot"
            )
        )
    
    else:  # development
        return AppConfig(
            network=NetworkConfig(
                default_port=3978,
                host="127.0.0.1",
                uvicorn_log_level="debug"
            ),
            auth=AuthConfig(
                jwt_leeway_seconds=600
            ),
            logger=LoggerConfig(
                app_logger_name="dev/bot"
            )
        )

# Usage
env = os.getenv("ENVIRONMENT", "development")
config = get_config(env)

app = App(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    tenant_id=os.getenv("TENANT_ID"),
    config=config
)
```

### Loading from Environment Variables

```python
import os
from microsoft.teams.apps import AppConfig, NetworkConfig, AuthConfig

def config_from_env() -> AppConfig:
    """Build config from environment variables."""
    return AppConfig(
        network=NetworkConfig(
            default_port=int(os.getenv("BOT_PORT", "3978")),
            host=os.getenv("BOT_HOST", "0.0.0.0"),
            user_agent=os.getenv("BOT_USER_AGENT"),
            uvicorn_log_level=os.getenv("LOG_LEVEL", "info")
        ),
        auth=AuthConfig(
            jwt_leeway_seconds=int(os.getenv("JWT_LEEWAY", "300")),
            default_graph_tenant_id=os.getenv("GRAPH_TENANT_ID", "botframework.com")
        )
    )

# Usage
config = config_from_env()
app = App(config=config)
```

## Testing Configuration

### Test Configuration with Mocked URLs

```python
from microsoft.teams.apps import AppConfig, EndpointConfig, AuthConfig

test_config = AppConfig(
    endpoints=EndpointConfig(
        bot_api_base_url="http://localhost:5001",  # Mock server
        activity_path="/test/messages"
    ),
    auth=AuthConfig(
        jwt_leeway_seconds=3600,  # Very forgiving for tests
        bot_framework_issuer="http://localhost:5001/issuer",
        bot_framework_jwks_uri="http://localhost:5001/keys"
    )
)
```

## Best Practices

1. **Create config once**: Build your `AppConfig` at application startup
2. **Use factory functions**: Create configuration based on environment
3. **Document custom values**: Add comments explaining why you changed defaults
4. **Test configurations**: Verify your custom config works in all environments
5. **Keep secrets separate**: Don't put credentials in config objects
6. **Version control**: Check in config templates, not actual configs with secrets

## Migration from Hardcoded Values

### Before (using hardcoded constants)

```python
from microsoft.teams.apps import App

# No way to customize port, URLs, etc.
app = App(
    client_id="...",
    client_secret="...",
    tenant_id="..."
)
# Port is always 3978 (or PORT env var)
```

### After (using AppConfig)

```python
from microsoft.teams.apps import App, AppConfig, NetworkConfig

# Full control over configuration
config = AppConfig(
    network=NetworkConfig(default_port=5000)
)

app = App(
    client_id="...",
    client_secret="...",
    tenant_id="...",
    config=config
)
# Port is now 5000 (or PORT env var)
```

## Future Configuration Options

The config system is designed to be extensible. Future versions may add:

- File-based configuration (YAML, JSON, TOML)
- Configuration validation
- Configuration hot-reload
- Environment-based config profiles
- Configuration schema export
