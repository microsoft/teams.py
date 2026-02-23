# Release Process

This document describes how to release packages for the Teams SDK for Python. It assumes you have required entitlements in Azure DevOps for triggering releases.

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

## Versioning

Versions are managed by **Nerdbank.GitVersioning** via [version.json](version.json).

### Current Configuration (`main`)

```json
{
  "version": "2.0.0-dev.{height}",
  "versionHeightOffset": 1
}
```

Builds on `main` produce dev versions like `2.0.0.dev1`, `2.0.0.dev2`, etc. These are not published.

### Alpha Branch (`alpha/v2.0.0`)

```json
{
  "version": "2.0.0-alpha.{height}",
  "versionHeightOffset": 10
}
```

Builds on `alpha/v2.0.0` produce alpha versions like `2.0.0a10`, `2.0.0a11`, etc. These are published.

### Example Package Names

| Branch | Package Name |
|--------|--------------|
| `alpha/v2.0.0` | `microsoft_teams_ai-2.0.0a11.tar.gz` |
| `release/v2.0.0` | `microsoft_teams_ai-2.0.0.tar.gz` |

> **Note:** Running the pipeline on a branch not in `publicReleaseRefSpec` (e.g., a feature branch) produces versions with the commit hash appended, like `2.0.0a11.dev5+g1a2b3c4`. This is expected and useful for testing.

### Producing a Stable Release

To produce a stable release (e.g., `2.0.0` without any suffix):

1. Create a `release/v2.0.0` branch from `alpha/v2.0.0`
2. Update its `version.json`:
   ```json
   {
     "version": "2.0.0",
     "versionHeightOffset": 1
   }
   ```
3. Run the publish pipeline with **Public** to release to PyPI

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

The [publish pipeline](https://dev.azure.com/DomoreexpGithub/Github_Pipelines/_build?definitionId=49&_a=summary) (`.azdo/publish.yml`) is manually triggered and requires selecting a **Publish Type**: `Internal` or `Public`.

1. Go to **Pipelines** > **teams.py** in ADO
2. Click **Run pipeline**
3. Select the branch to build from (e.g., `alpha/v2.0.0`)
4. Choose a **Publish Type**:
   - **Internal** — publishes unsigned packages to the Azure Artifacts `TeamsSDKPreviews` feed. No approval required. Packages are available immediately.
   - **Public** — signs packages via ESRP and publishes to PyPI. Requires approval via the `teams-sdk-publish` ADO environment before the ESRP release proceeds.
5. Pipeline runs: Build > Test > Publish

> **Note:** The `devtools` package is excluded from publishing. The pipeline filters out packages matching the `ExcludePackageFolders` variable. Prerelease versions are tagged `next` on PyPI; stable versions are tagged `latest`.

#### Installing Published Packages

```bash
pip install microsoft-teams-ai==2.0.0a11
```

## Approvers

The `teams-sdk-publish` environment in Azure DevOps controls who can approve public releases. To modify approvers:

1. Go to **Pipelines** > **Environments** in ADO
2. Select **teams-sdk-publish**
3. Click the **three dots** menu > **Approvals and checks**
4. Add/remove approvers as needed
