# Release Process

This project uses [Nerdbank.GitVersioning](https://github.com/dotnet/Nerdbank.GitVersioning) for automatic version management.

## Prerequisites

```bash
dotnet tool install -g nbgv
```

## Version Lifecycle

| Branch | version.json | Produces |
|--------|--------------|----------|
| `main` | `2.0.0-alpha.{height}` (offset: 10) | `2.0.0a10`, `2.0.0a11`, ... |
| `release/v2.0.0-beta` | `2.0.0-beta.{height}` | `2.0.0b1`, `2.0.0b2`, ... |
| `release/v2.0.0` | `2.0.0` | `2.0.0` |

## Creating a Release

1. Create branch from main (e.g., `release/v2.0.0-beta`)
2. Update `version.json` with the appropriate version format
3. Push and trigger the [release pipeline](https://dev.azure.com/DomoreexpGithub/Github_Pipelines/_build?definitionId=49&_a=summary)

## Publishing a New Package

1. Go to [PyPI publishing](https://pypi.org/manage/account/publishing/)
2. Add: owner `microsoft`, repo `teams.py`, workflow `release.yml`, environment `release`
