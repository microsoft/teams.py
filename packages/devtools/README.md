> [!WARNING]
> **Deprecated** — This package was originally in preview, but we have decided to stop maintaining it before General Availability. We recommend testing with Microsoft Teams directly, or with the [Agents Playground](https://learn.microsoft.com/en-us/microsoftteams/platform/toolkit/debug-your-agents-playground).

# Microsoft Teams DevTools

<p>
    <a href="https://pypi.org/project/microsoft-teams-devtools" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-devtools" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-devtools" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-devtools" />
    </a>
    <a href="https://microsoft.github.io/teams-sdk" target="_blank">
        <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
    </a>
</p>

[📖 Documentation](https://microsoft.github.io/teams-sdk/developer-tools/devtools/)

Developer tools for locally testing and debugging Teams applications. Streamlines the development process by eliminating the need to deploy apps or expose public endpoints during development.

## Installation

```bash
pip install microsoft-teams-devtools
```

Or if using uv:

```bash
uv add microsoft-teams-devtools
```

## Usage

```python
from microsoft_teams.apps import App
from microsoft_teams.devtools import DevToolsPlugin

app = App()
app.use(DevToolsPlugin())

await app.start()
# Open http://localhost:3979/devtools in your browser
```
