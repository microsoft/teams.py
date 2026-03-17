# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Microsoft Teams Python SDK — a UV workspace with multiple packages providing APIs, common utilities, and integrations for Microsoft Teams.

## Development Setup

### Prerequisites
- UV >= 0.8.11
- Python >= 3.12

### Commands
```bash
uv sync                    # Install virtual env and dependencies
source .venv/bin/activate  # Activate virtual environment
pre-commit install         # Install pre-commit hooks

poe fmt                    # Format code with ruff
poe lint                   # Lint code with ruff
poe check                  # Run both format and lint
poe test                   # Run tests with pytest
pyright                    # Run type checker
```

## Tooling

- **Formatter/Linter**: Ruff — line length 120, rules: E, F, W, B, Q, I, ASYNC
- **Type checker**: Pyright
- **Test framework**: pytest + pytest-asyncio (Ruff bans importing the unittest test framework; unittest.mock is allowed and used)

## Architecture

### Workspace Structure
All packages live in `packages/`, each with `src/microsoft_teams/<package>/` layout:

| Package | Description |
|---------|-------------|
| `api` | Core API clients, models (Account, Activity, Conversation), auth |
| `apps` | App orchestrator, plugins, routing, events, HttpServer |
| `common` | HTTP client abstraction, logging, storage |
| `cards` | Adaptive cards |
| `ai` | AI/function calling utilities |
| `botbuilder` | Bot Framework integration plugin |
| `devtools` | Development tools plugin |
| `mcpplugin` | MCP server plugin |
| `a2aprotocol` | A2A protocol plugin |
| `graph` | Microsoft Graph integration |
| `openai` | OpenAI integration |

### Key Patterns

**Imports**
- ALL imports MUST be at the top of the file — no imports inside functions, classes, or conditional blocks
- Avoid `TYPE_CHECKING` blocks unless absolutely necessary (genuine circular imports that can't be restructured)
- Avoid dynamic/deferred imports unless absolutely necessary
- Relative imports within the same package, absolute for external packages

**Models**
- Pydantic with `ConfigDict(alias_generator=to_camel)` — snake_case in Python, camelCase in JSON
- `model_dump(by_alias=True)` for serialization, `model_dump(exclude_none=True)` for query params

**Interfaces**
- Protocol classes instead of Abstract Base Classes (ABC)
- Prefer composition over inheritance

**Clients**
- Concrete clients inherit from `BaseClient` (`packages/api/src/microsoft_teams/api/clients/base_client.py`)
- Composition with operation classes for sub-functionality
- async/await for all API calls, return domain models

## Scaffolding (cookiecutter)

```bash
cookiecutter templates/package -o packages   # New package
cookiecutter templates/test -o tests         # New test package
```

## Dependencies and Build

- UV workspace — packages reference each other via `{ workspace = true }`
- Hatchling build backend
- Dev dependencies in root `pyproject.toml`
