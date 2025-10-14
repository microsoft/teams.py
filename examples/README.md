# Configuration Examples

This directory contains examples demonstrating how to use the `AppConfig` system in microsoft-teams-apps.

## Files

- **config_example.py** - Complete example showing development and production configurations

## Running the Examples

### Development Mode (default)

```bash
python examples/config_example.py
```

### Production Mode

```bash
ENVIRONMENT=production python examples/config_example.py
```

## What's Demonstrated

The examples show how to:

1. Create custom `AppConfig` instances
2. Configure different settings for development vs production
3. Use all configuration categories:
   - `NetworkConfig` - Server settings
   - `AuthConfig` - Authentication settings
   - `RetryConfig` - Retry behavior
   - `SignInConfig` - Sign-in UI customization

## Learn More

- See [CONSTANTS_AUDIT.md](../CONSTANTS_AUDIT.md) for a complete list of all configurable constants
- See [CONFIG_USAGE_EXAMPLES.md](../CONFIG_USAGE_EXAMPLES.md) for comprehensive usage examples
- See [packages/apps/tests/test_config.py](../packages/apps/tests/test_config.py) for test examples

## Note

The `AppConfig` object is fully functional, but integration with the `App` class is pending.
You can create and use config objects now, and they will be automatically supported once
the integration is complete.
