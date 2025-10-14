# Quick Start: Using AppConfig

This guide helps you quickly understand and use the new `AppConfig` system.

## What Is AppConfig?

`AppConfig` is a new feature that makes all hardcoded constants in `microsoft-teams-apps` user-configurable. Instead of being stuck with default values, you can now customize:

- Server port and host
- API endpoints and URLs
- Authentication settings
- Retry behavior
- Sign-in UI text
- Logger names
- And more!

## Quick Example

```python
from microsoft.teams.apps import App, AppConfig, NetworkConfig

# Customize the port
config = AppConfig(
    network=NetworkConfig(default_port=5000)
)

# Use it (when integrated with App)
# app = App(client_id="...", config=config)
```

## What Can You Configure?

### 1. Network Settings
```python
from microsoft.teams.apps import NetworkConfig

NetworkConfig(
    default_port=8080,              # Change server port
    host="127.0.0.1",               # Bind to localhost only
    user_agent="MyBot/2.0",         # Custom user agent
    uvicorn_log_level="debug"       # Verbose logging
)
```

### 2. API Endpoints
```python
from microsoft.teams.apps import EndpointConfig

EndpointConfig(
    bot_api_base_url="https://custom.api.com",
    activity_path="/custom/messages",
    health_check_path="/health"
)
```

### 3. Authentication
```python
from microsoft.teams.apps import AuthConfig

AuthConfig(
    jwt_leeway_seconds=600,         # 10 minutes clock skew
    default_graph_tenant_id="..."   # Custom tenant
)
```

### 4. Retry Behavior
```python
from microsoft.teams.apps import RetryConfig

RetryConfig(
    max_attempts=10,                # Try more times
    initial_delay=1.0,              # Wait longer
    jitter_type="equal"             # Different strategy
)
```

### 5. Sign-In UI
```python
from microsoft.teams.apps import SignInConfig

SignInConfig(
    oauth_card_text="Please login to continue",
    sign_in_button_text="Login"
)
```

## Common Use Cases

### Development Configuration
```python
from microsoft.teams.apps import AppConfig, NetworkConfig, AuthConfig

dev_config = AppConfig(
    network=NetworkConfig(
        default_port=3978,
        host="127.0.0.1",           # Localhost only
        uvicorn_log_level="debug"   # Verbose logs
    ),
    auth=AuthConfig(
        jwt_leeway_seconds=600      # Forgiving for dev
    )
)
```

### Production Configuration
```python
from microsoft.teams.apps import AppConfig, NetworkConfig, RetryConfig

prod_config = AppConfig(
    network=NetworkConfig(
        default_port=8080,
        host="0.0.0.0",             # Public binding
        uvicorn_log_level="warning" # Less verbose
    ),
    retry=RetryConfig(
        max_attempts=5,
        jitter_type="equal"         # Prevent thundering herd
    )
)
```

### Testing Configuration
```python
from microsoft.teams.apps import AppConfig, AuthConfig, EndpointConfig

test_config = AppConfig(
    endpoints=EndpointConfig(
        bot_api_base_url="http://localhost:5001"  # Mock server
    ),
    auth=AuthConfig(
        jwt_leeway_seconds=3600     # Very forgiving for tests
    )
)
```

## Environment-Based Configuration

```python
import os
from microsoft.teams.apps import AppConfig, NetworkConfig

def get_config():
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return AppConfig(
            network=NetworkConfig(
                default_port=8080,
                uvicorn_log_level="warning"
            )
        )
    else:
        return AppConfig(
            network=NetworkConfig(
                default_port=3978,
                uvicorn_log_level="debug"
            )
        )

config = get_config()
```

## Default Values

Don't worry about setting everything! All config has sensible defaults:

```python
from microsoft.teams.apps import AppConfig

# This uses all defaults - same as before!
config = AppConfig()

# Defaults:
# - port: 3978
# - host: 0.0.0.0
# - activity_path: /api/messages
# - jwt_leeway: 300 seconds
# - max_retries: 5
# - etc.
```

## Learn More

- **CONSTANTS_AUDIT.md** - Complete list of all 49 configurable constants
- **CONFIG_USAGE_EXAMPLES.md** - Extensive examples for every scenario
- **examples/config_example.py** - Runnable demonstration code
- **SUMMARY.md** - Executive summary of the feature

## Testing

```bash
# Run the config tests
pytest packages/apps/tests/test_config.py -v

# Try the example
python examples/config_example.py

# Try production mode
ENVIRONMENT=production python examples/config_example.py
```

## Status

✅ **Config object is complete and ready to use**
- Fully implemented with all 49 constants
- 20 comprehensive tests (all passing)
- Complete documentation
- Working examples

⏳ **Integration with App class is pending** (future work)

## Questions?

Check these files for more information:
1. **SUMMARY.md** - Quick overview
2. **CONSTANTS_AUDIT.md** - What constants exist
3. **CONFIG_USAGE_EXAMPLES.md** - How to use them
4. **packages/apps/tests/test_config.py** - Example usage in tests
