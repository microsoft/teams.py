> [!CAUTION]
> This project is in public preview. We’ll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

# Microsoft Teams SDK for Python

A comprehensive SDK for building Microsoft Teams applications, bots, and AI agents using Python. This SDK provides a high-level framework with built-in Microsoft Graph integration, OAuth handling, and extensible plugin architecture.

<a href="https://microsoft.github.io/teams-sdk" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Questions & Issues

- **Questions or Feature Requests**: Please use [GitHub Discussions](https://github.com/microsoft/teams-sdk/discussions)
- **Bug Reports**: Please [open an issue](https://github.com/microsoft/teams.py/issues/new/choose)

- [Getting Started](#getting-started)
- [Packages](#packages)
- [Test Apps](#test-apps)
- [Links](#links)

## Getting Started

### Prerequisites

- UV version is >= 0.8.11. Install and upgrade from [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).
- Python version is >= 3.12. Install or upgrade from [python.org/downloads](https://www.python.org/downloads/).

### Installation

#### 1. Install the dependencies.

```bash
 uv sync --all-packages --group dev
```

#### 2. Activate the virtual env

> **Note:** After the initial setup, you need to activate the virtual environment each time you start a new terminal session

```bash
# On Mac
 `source .venv/bin/activate`

# On Windows
 `.venv\Scripts\Activate`
```

#### 3. Install the pre-commit hooks

```bash
 pre-commit install
```

## Packages

> ℹ️ core packages used to build client/server apps for Teams.

- [`microsoft-teams-apps`](./packages/apps/README.md)
- [`microsoft-teams-ai`](./packages/ai/README.md)
- [`microsoft-teams-api`](./packages/api/README.md)
- [`microsoft-teams-cards`](./packages/cards/README.md)
- [`microsoft-teams-common`](./packages/common/README.md)
- [`microsoft-teams-devtools`](./packages/devtools/README.md)
- [`microsoft-teams-graph`](./packages/graph/README.md)
- [`microsoft-teams-openai`](./packages/openai/README.md)
- [`microsoft-teams-botbuilder`](./packages/botbuilder/README.md)

> external packages to integrate with external protocols and microsoft-teams-cards

- [`microsoft-teams-mcpplugin`](./packages/mcpplugin/README.md)
- [`microsoft-teams-a2a`](./packages/a2aprotocol/README.md)

### Create a New Package

We use [cookiecutter](https://cookiecutter.readthedocs.io/en/latest/README.html) to create new packages. To create a new package, run:

```bash
cookiecutter templates/package -o packages
```

Follow the prompts to name the package and the directory. It should create the package folder in the `packages` directory.

### Create A New Test Package

Similarly, to create a new test package, run:

```bash
cookiecutter templates/test -o tests
```

## Test Apps

> ℹ️ used to test the SDK or as a visual sample of how certain features can be implemented.

> ⚠️ **WARNING** these apps are changed often and are not intended to be used outside the
> projects monorepo. To easily setup a new project please use the **templates** available via
> the [@microsoft/teams.cli](https://www.npmjs.com/package/@microsoft/teams.cli) and follow the
> [Getting Started](https://microsoft.github.io/teams-sdk/python/getting-started) documentation!

- [`@examples/echo`](./examples/echo/README.md)
- [`@examples/message-extensions`](./examples/message-extensions/README.md)
- [`@examples/dialogs`](./examples/dialogs/README.md)
- [`@examples/graph`](./examples/graph/README.md)
- [`@examples/ai-test`](./examples/ai-test/README.md)
- [`@examples/stream`](./examples/stream/README.md)
- [`@examples/oauth`](./examples/oauth/README.md)

## Links

- [Teams Developer Portal: Apps](https://dev.teams.microsoft.com/apps)
- [Teams Toolkit](https://www.npmjs.com/package/@microsoft/teamsapp-cli)
