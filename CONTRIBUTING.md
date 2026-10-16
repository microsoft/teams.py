Please refer to this sub-module's root repo Contributing guide at [Teams SDK Contributing](https://github.com/microsoft/teams-ai/blob/main/CONTRIBUTING.md)

## Multi-Language SDK

The Teams SDK is maintained across three languages: **Python**, **TypeScript**, and **.NET**. When proposing new features, please discuss them in a language-agnostic way in [GitHub Discussions](https://github.com/microsoft/teams-sdk/discussions). This ensures that features can be implemented consistently across all three SDKs and benefits the entire Teams developer community.

## Mocking HTTP in unit tests

Construct `httpx.AsyncClient(transport=httpx.MockTransport(handler), ...)` and inject it into the SDK's
`Client` via `_http`. Do not replace `client.http._transport` after construction: HTTPX may already have
configured proxy mounts from the host environment, which can route requests around the mock. When
cloning test clients, preserve the mock transport along with the client's settings and event hooks.

## Integration Tests

Integration tests live in `tests/integration/` and make real API calls against the Teams Bot Framework service.

**When to add:** If your change affects what goes on the wire (URL, headers, body, auth token) or how a response is parsed, add an integration test. See the [cross-SDK runbook](https://github.com/microsoft/teams-sdk/blob/main/INTEGRATION-TESTS.md) for full guidelines.

**Running locally:**

```bash
uv sync --all-packages --group dev --group integration
set -a; source tests/integration/.env.botid-prod; set +a
pytest tests/integration -v
```