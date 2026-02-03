# Release Process

This project uses [Nerdbank.GitVersioning](https://github.com/dotnet/Nerdbank.GitVersioning) for automatic version management.

## Prerequisites

```bash
dotnet tool install -g nbgv
```

## Branch Strategy

| Branch | Versions | Published |
|--------|----------|-----------|
| `main` | `2.0.0.dev1`, `2.0.0.dev2`, ... | No |
| `alpha/v2.0.0` | `2.0.0a10`, `2.0.0a11`, ... | Yes |
| `release/v2.0.0` | `2.0.0` | Yes |

## Workflow

Development happens on `main`. When ready to release, merge via PR:

```
main → alpha/v2.0.0 → release/v2.0.0
```

Each merge increments the version automatically.

## Creating a New Alpha Branch

When starting a new version (e.g., 2.1.0):

1. Create `alpha/v2.1.0` from `main`
2. Update its `version.json`:
   ```json
   {
     "version": "2.1.0-alpha.{height}",
     "versionHeightOffset": 1
   }
   ```
3. Set up branch protection (require PRs)

## Publishing

1. Open PR: `main` → `alpha/v2.0.0`
2. Merge PR (version auto-increments)
3. Trigger the [release pipeline](https://dev.azure.com/DomoreexpGithub/Github_Pipelines/_build?definitionId=49&_a=summary)
