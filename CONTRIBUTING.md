Please refer to this sub-module's root repo Contributing guide at [Teams SDK Contributing](https://github.com/microsoft/teams-ai/blob/main/CONTRIBUTING.md)

## Multi-Language SDK

The Teams SDK is maintained across three languages: **Python**, **TypeScript**, and **.NET**. When proposing new features, please discuss them in a language-agnostic way in [GitHub Discussions](https://github.com/microsoft/teams-sdk/discussions). This ensures that features can be implemented consistently across all three SDKs and benefits the entire Teams developer community.

## Integration Tests

Integration tests live in `tests/integration/` and make real API calls against the Teams Bot Framework service.

**When to add:** If your change affects what goes on the wire (URL, headers, body, auth token) or how a response is parsed, add an integration test. See the [cross-SDK runbook](https://github.com/microsoft/teams-sdk/blob/main/INTEGRATION-TESTS.md) for full guidelines.

**Running locally:**

```bash
uv sync --all-packages --group dev --group integration
export $(cat tests/integration/.env.botid-prod | xargs)
pytest tests/integration -v
```