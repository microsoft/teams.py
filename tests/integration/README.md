# Integration Tests

This directory contains integration tests that make real API calls against the Teams Bot Framework service.

## Prerequisites

- Python >= 3.11
- UV installed
- A `.env.botid-prod` file with valid credentials (see `.env.example`)

## Setup

```bash
# From repo root — install all deps including integration group
uv sync --all-packages --group dev --group integration
```

## Running Tests

```bash
# From repo root — load env and run
set -a; source tests/integration/.env.botid-prod; set +a
pytest tests/integration -v

# Run a specific test file
pytest tests/integration/test_activities.py -v

# Run a specific test
pytest tests/integration -k "test_create_activity" -v
```

## Architecture

- **`conftest.py`** — Per-test fixture that creates a fresh credential and API client on each test's event loop. Config and member lists are cached at module level to avoid repeated API calls.
- Tests are async (`pytest-asyncio` with `asyncio_mode = "auto"`).

## Known Limitations

- **AgentUser**: Reactions and paged members are not supported.
- **Canary ring**: Reactions return 404, paged members return empty.
- **Throttling**: Member caching prevents 429s but full-suite runs may still hit rate limits.

## Cross-SDK Runbook

For provisioning, secret rotation, and troubleshooting:

👉 [Integration Test Runbook](https://dev.azure.com/DomoreexpGithub/Github_Pipelines/_wiki/wikis/Github%20Pipelines%20Wiki/1/Teams-SDK-Integration-Test-Runbook) (internal only)
