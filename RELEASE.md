# Release Process

This project uses [Nerdbank.GitVersioning](https://github.com/dotnet/Nerdbank.GitVersioning) for automatic version management.

## Prerequisites

```bash
dotnet tool install -g nbgv
```

## Version Lifecycle

| Stage | Branch | Produces |
|-------|--------|----------|
| Alpha | `main` | `2.0.0a10`, `2.0.0a11`, ... |
| Beta | `release/v2.0.0` | `2.0.0b1`, `2.0.0b2`, ... |
| Stable | `release/v2.0.0` | `2.0.0` |

## Creating a Release

Use `nbgv prepare-release` to create a release branch:

```bash
nbgv prepare-release [tag]
```

This will:
1. Create a release branch with the specified prerelease tag (or stable if omitted)
2. Bump main to the next alpha version

Then push and trigger the [release pipeline](https://dev.azure.com/DomoreexpGithub/Github_Pipelines/_build?definitionId=49&_a=summary).

## Publishing a New Package

1. Go to [PyPI publishing](https://pypi.org/manage/account/publishing/)
2. Add: owner `microsoft`, repo `teams.py`, workflow `release.yml`, environment `release`
