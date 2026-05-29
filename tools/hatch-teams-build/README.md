# hatch-teams-build

Hatchling plugin for the Teams Python SDK. Provides two build-time hooks:

## Version Source (`teams-build`)

Calls the `nbgv` CLI directly to resolve package versions from git history via [Nerdbank.GitVersioning](https://github.com/dotnet/Nerdbank.GitVersioning), then normalizes the result with PyPA `packaging`. Falls back to `0.0.0` when the `nbgv` CLI is not installed, so local development works without .NET SDK. Set `NBGV_REQUIRED=1` to make a missing or failing CLI a hard error (used in CI).

```toml
[tool.hatch.version]
source = "teams-build"
```

## Metadata Hook (`teams-build`)

Rewrites bare `microsoft-teams-*` dependencies to include `>=<current_version>` at build time. This ensures published wheels enforce compatible sibling package versions.

```toml
[tool.hatch.metadata.hooks.teams-build]
```

**Example:** if the current nbgv version is `2.0.0a49`, a dependency listed as `microsoft-teams-common` becomes `microsoft-teams-common>=2.0.0a49` in the built wheel metadata.

When nbgv is unavailable (fallback `0.0.0`), the hook skips rewriting entirely — dependencies stay bare, which is correct for local development where UV workspace resolution handles everything.

## Usage

Each package pyproject.toml needs:

```toml
[build-system]
requires = ["hatchling", "hatch-teams-build"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "teams-build"

[tool.hatch.metadata.hooks.teams-build]
```

## Verification

```bash
uv build packages/apps --sdist
# Inspect PKG-INFO — workspace deps should show >=<version>
```
