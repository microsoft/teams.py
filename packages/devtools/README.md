> [!CAUTION]
> This project is in public preview. We’ll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

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
uv add microsoft-teams-devtools
```

## Usage

```python
from microsoft.teams.apps import App
from microsoft.teams.devtools import DevToolsPlugin

app = App()
app.use(DevToolsPlugin())

await app.start()
# Open http://localhost:3979/devtools in your browser
```
