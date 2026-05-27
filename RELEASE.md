# Release Process

This document describes how to release packages for the Teams SDK for Python. It assumes you have required entitlements in Azure DevOps for triggering releases.

This project uses [Nerdbank.GitVersioning](https://github.com/dotnet/Nerdbank.GitVersioning) for automatic version management.

## Prerequisites

The .NET SDK and `nbgv` CLI are **required for publishing** but **optional for local development**. Without them, packages fall back to version `0.0.0` so you can still build and test locally.

CI pipelines set `NBGV_REQUIRED=1` to ensure builds fail if `nbgv` is unavailable.

```bash
# Optional for local dev, required for releases
dotnet tool install -g nbgv
```

## Branch Strategy

| Branch | Versions | Published |
|--------|----------|-----------|
| `main` | `2.0.1.dev1`, `2.0.1.dev2`, ... | No |
| `release` | `2.0.0` | Yes |

## Workflow

Development happens on `main`. When ready to release, create a `release` branch from `main`:

```
main → release
```

## Versioning

Versions are managed by **Nerdbank.GitVersioning** via [version.json](version.json).

### Current Configuration (`main`)

```json
{
  "version": "2.0.1-dev.{height}",
  "versionHeightOffset": 1
}
```

Builds on `main` produce dev versions like `2.0.1.dev1`, `2.0.1.dev2`, etc. These are not published.

### Example Package Names

| Branch | Package Name |
|--------|--------------|
| `main` | `microsoft_teams_apps-2.0.1.dev2.tar.gz` |
| `release` | `microsoft_teams_apps-2.0.0.tar.gz` |

> **Note:** Running the pipeline on a branch not in `publicReleaseRefSpec` (e.g., a feature branch) produces versions with the commit hash appended, like `2.0.1.dev5+g1a2b3c4`. This is expected and useful for testing.

### Producing a Stable Release

To produce a stable release (e.g., `2.0.0` without any suffix):

1. Create a `release` branch from `main`
2. Update its `version.json`:
   ```json
   {
     "version": "2.0.0",
     "versionHeightOffset": 1
   }
   ```
3. Run the publish pipeline with **Public** to release to PyPI

## Publishing

The [publish pipeline](https://dev.azure.com/DomoreexpGithub/Github_Pipelines/_build?definitionId=51&_a=summary) (`.azdo/publish.yml`) is manually triggered and requires selecting a **Publish Type**: `Internal` or `Public`.

1. Go to **Pipelines** > **teams.py** in ADO
2. Click **Run pipeline**
3. Select the `release` branch
4. Choose a **Publish Type**:
   - **Internal** — publishes unsigned packages to the Azure Artifacts `TeamsSDKPreviews` feed. No approval required. Packages are available immediately.
   - **Public** — signs packages via ESRP and publishes to PyPI. Requires approval via the `teams-sdk-publish` ADO environment before the ESRP release proceeds.
5. Pipeline runs: Build > Test > Publish

> **Note:** The pipeline filters out packages matching the `ExcludePackageFolders` variable. Prerelease versions are tagged `next` on PyPI; stable versions are tagged `latest`.

#### Installing Published Packages

```bash
pip install microsoft-teams-apps==2.0.0
```

## Approvers

The `teams-sdk-publish` environment in Azure DevOps controls who can approve public releases. To modify approvers:

1. Go to **Pipelines** > **Environments** in ADO
2. Select **teams-sdk-publish**
3. Click the **three dots** menu > **Approvals and checks**
4. Add/remove approvers as needed
