> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams DevTools

Developer tools for locally testing and debugging Teams applications. Streamlines the development process by eliminating the need to deploy apps or expose public endpoints during development.

## Features

- **Local Testing**: Test Teams apps locally without deployment
- **Bot Emulator**: Simulate Teams conversations and interactions
- **Graph API Testing**: Test Microsoft Graph integrations offline
- **OAuth Simulation**: Mock OAuth flows for development
- **Debug Tools**: Enhanced logging and debugging capabilities
- **Hot Reload**: Automatic app reloading during development

## Usage

```python
from microsoft.teams.devtools import LocalTestRunner

# Create local test environment
runner = LocalTestRunner(app)

# Start local testing server
await runner.start()
```

## Development Workflow

1. **Local Development**: Build and test without Teams deployment
2. **Graph Testing**: Validate Graph API integrations with mock tokens
3. **OAuth Flow Testing**: Test authentication flows locally
4. **Debug Mode**: Enhanced logging and error reporting
5. **Performance Profiling**: Monitor app performance metrics

This package accelerates Teams app development by providing a complete local testing environment.