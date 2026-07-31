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
| `main` | `2.1.0.dev1`, `2.1.0.dev2`, ... | No |
| `release/v2.0` | `2.0.x` | Yes |

Release branches are **long-lived per minor line** and use the `release/v<major>.<minor>` naming convention. Create a
new release branch from `main` when that minor line enters its release phase; never reset an existing release branch.

## Workflow

Development happens on `main`. When ready to release:

1. Open a PR from a feature branch (e.g. `<you>/release-2.1.0`) into the matching release branch
   (e.g. `release/v2.1`)
2. The PR should make the release branch equal `main` plus the version bump in `version.json`
3. Merge the PR, then run the publish pipeline

### Preparing the release branch

Start from `main`, bump the version, then use `git merge -s ours origin/release/v<major>.<minor>` to mark the target
release branch as merged without pulling in any of its content.

1. Start a branch from latest `main`:
   ```bash
   git fetch origin
   git checkout -b <you>/prep-release-<version> origin/main
   ```

2. Edit `version.json` and change `"version"` from `"X.Y.Z-dev.{height}"` to `"X.Y.Z"` (the stable version you're releasing), then commit:
   ```bash
   git add version.json
   git commit -m "Release <version>: set version to <version> stable"
   ```

3. Merge the target release branch into your branch using `-s ours` (records it as a parent but keeps main's tree):
   ```bash
   git merge -s ours origin/release/v<major>.<minor> -m "Release <version>: merge main into release/v<major>.<minor>"
   ```

4. Push and open a PR targeting the matching release branch:
   ```bash
   git push -u origin <you>/prep-release-<version>
   gh pr create --base "release/v<major>.<minor>" --title "Release <version>: merge main into release/v<major>.<minor>"
   ```

## Versioning

Versions are managed by **Nerdbank.GitVersioning** via [version.json](version.json).

### Current Configuration (`main`)

```json
{
  "version": "2.1.0-dev.{height}",
  "versionHeightOffset": 1
}
```

Builds on `main` produce dev versions like `2.1.0.dev1`, `2.1.0.dev2`, etc. These are not published. Changing the
version core resets Nerdbank.GitVersioning's height for the new development line, so the offset remains `1`.

### Example Package Names

| Branch | Package Name |
|--------|--------------|
| `main` | `microsoft_teams_apps-2.1.0.dev2.tar.gz` |
| `release/v2.0` | `microsoft_teams_apps-2.0.14.tar.gz` |

> **Note:** Running the pipeline on a branch not in `publicReleaseRefSpec` (e.g., a feature branch) produces versions with the commit hash appended, like `2.1.0.dev5+g1a2b3c4`. This is expected and useful for testing.

### Producing a Stable Release

The version on a release branch should be a plain stable string (e.g. `2.1.0`, no `-dev` suffix). The PR opened in
the [Workflow](#workflow) section above already handles this — just edit `version.json` before pushing:

```json
{
  "version": "2.1.0",
  "versionHeightOffset": 1
}
```

After the PR merges, run the publish pipeline with **Public** to release to PyPI.

## Publishing

The [publish pipeline](https://dev.azure.com/DomoreexpGithub/Github_Pipelines/_build?definitionId=51&_a=summary) (`.azdo/publish.yml`) is manually triggered and requires selecting a **Publish Type**: `Internal` or `Public`.

1. Go to **Pipelines** > **teams.py** in ADO
2. Click **Run pipeline**
3. Select the matching `release/v<major>.<minor>` branch
4. Choose a **Publish Type**:
   - **Internal** — publishes unsigned packages to the Azure Artifacts `TeamsSDKPreviews` feed. No approval required. Packages are available immediately.
   - **Public** — signs packages via ESRP and publishes to PyPI. Requires approval via the `teams-sdk-publish` ADO environment before the ESRP release proceeds.
5. Pipeline runs: Build > Test > Publish

> **Note:** The pipeline filters out packages matching the `ExcludePackageFolders` variable. Prerelease versions are tagged `next` on PyPI; stable versions are tagged `latest`.

## Tagging and GitHub Release

After the publish pipeline finishes and packages land on PyPI, tag the release and create a GitHub Release page:

```bash
# Create a draft release at the matching release branch tip
gh release create v<version> -R microsoft/teams.py \
  --target "release/v<major>.<minor>" --title "v<version>" --draft \
  --generate-notes --notes-start-tag v<previous-version>
```

**Note:** GitHub's auto-generated notes walk back from the release branch tip. Because the release PR is
squash-merged, the auto-list shows only the merge PR. To get the real PR delta from `main`, query by date:

```bash
# Note: macOS has no `tac` — the awk one-liner below works everywhere
gh api -X GET search/issues \
  -f q='repo:microsoft/teams.py is:pr is:merged base:main merged:>=<previous-release-publish-date>' \
  --jq '.items[] | "* \(.title) by @\(.user.login) in \(.html_url)"' \
  | awk '{ a[NR] = $0 } END { for (i = NR; i >= 1; i--) print a[i] }' \
  > /tmp/notes.md
```

Paste the curated list into the draft, then publish from the GitHub UI (or via `gh release edit --draft=false`) to create the tag.

## Approvers

The `teams-sdk-publish` environment in Azure DevOps controls who can approve public releases. To modify approvers:

1. Go to **Pipelines** > **Environments** in ADO
2. Select **teams-sdk-publish**
3. Click the **three dots** menu > **Approvals and checks**
4. Add/remove approvers as needed
