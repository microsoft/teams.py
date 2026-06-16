# Integration Tests

This directory contains integration tests that make real API calls against the Teams Bot Framework service.

## Prerequisites

- Python >= 3.12
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
dotenv -f tests/integration/.env.botid-prod run -- pytest tests/integration -v

# Or export vars manually
export $(cat tests/integration/.env.botid-prod | xargs)
pytest tests/integration -v

# Run a specific test file
pytest tests/integration/test_activities.py -v

# Run a specific test
pytest tests/integration -k "test_create_activity" -v
```

## Architecture

- **`conftest.py`** — Shared fixture with async token acquisition (azure-identity), member caching, and config loading.
- Tests use a singleton fixture pattern — auth and member lookup happen once per session.
- Tests are async (`pytest-asyncio` with `asyncio_mode = "auto"`).

## Known Limitations

- **Agentic identity**: Reactions and paged members are not supported.
- **Canary ring**: Reactions return 404, paged members return empty.
- **Throttling**: Member caching prevents 429s but full-suite runs may still hit rate limits.

## Cross-SDK Runbook

For provisioning, secret rotation, and troubleshooting:

👉 [INTEGRATION-TESTS.md](https://github.com/microsoft/teams-sdk/blob/main/INTEGRATION-TESTS.md)
