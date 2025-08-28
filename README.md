> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams AI SDK for Python

A comprehensive SDK for building Microsoft Teams applications, bots, and AI agents using Python. This SDK provides a high-level framework with built-in Microsoft Graph integration, OAuth handling, and extensible plugin architecture.

## Key Features

- **Teams Bot Framework**: Complete bot development framework with activity routing
- **Microsoft Graph Integration**: Built-in Graph API clients with automatic token management
- **OAuth & Authentication**: Seamless user authentication and token lifecycle management
- **Plugin Architecture**: Extensible system for adding custom functionality

## Package Structure

- **`packages/apps/`** - High-level Teams application framework
- **`packages/api/`** - Core API clients and models for Teams Bot Framework
- **`packages/graph/`** - Microsoft Graph API integration with TokenProtocol
- **`packages/common/`** - Shared utilities (HTTP, logging, storage, events)
- **`packages/cards/`** - Adaptive Cards functionality
- **`packages/devtools/`** - Development and debugging tools
- **`tests/`** - Demo applications showcasing various features

## Quick Examples

### Graph Integration Demo

Located in `tests/graph/` - showcases Microsoft Graph API usage with user authentication, profile access, Teams membership, and email integration.

### OAuth Flow Demo

Located in `tests/oauth/` - demonstrates user authentication and token management.

### Message Extensions Demo

Located in `tests/message-extensions/` - shows how to build Teams message extensions.

## Getting Started

### Prerequisites

Note: Ensure uv version is >= 0.8.11
Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Installing

1. `uv sync --all-packages --group dev` - it installs the virtual env and dependencies
   - If you are using Windows, you may need to manually install [cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html)
2. Activate virtual env

- Mac: `source .venv/bin/activate`
- Windows: `.venv\Scripts\Activate`

> **Note:** After the initial setup, you need to activate the virtual environment each time you start a new terminal session

3. Install pre-commit hooks: `pre-commit install`

## Creating a new package

We use [cookiecutter](https://cookiecutter.readthedocs.io/en/latest/README.html) to create new packages. To create a new package, run:

```bash
cookiecutter templates/package -o packages
```

Follow the prompts to name the package and the directory. It should create the package folder in the `packages` directory.

## Creating a new test package

Similarly, to create a new test package, run:

```bash
cookiecutter templates/test -o tests
```
