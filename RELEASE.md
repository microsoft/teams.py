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

| Branch | Versions | PyPI tag | Published |
|--------|----------|----------|-----------|
| `main` | `2.1.0.dev1`, `2.1.0.dev2`, ... | n/a | No |
| `release/v2.0` | `2.0.x` (stable) | `latest` | Yes |
| `release/v2.1` | `2.1.0-alpha.N` (preview) | `next` | Yes |

Release branches are **long-lived per minor line** and use the `release/v<major>.<minor>` naming convention. Create a
new release branch from `main` when that minor line enters its release phase; never reset an existing release branch.

**Several release branches are live at once.** At the time of writing, `release/v2.0` carries the stable line and `release/v2.1` carries the preview line. A fix that affects both must be backported to each one separately, and each gets its own release. See [Backporting a fix to a release branch](#backporting-a-fix-to-a-release-branch).

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

## Backporting a fix to a release branch

The workflow above cuts a release by bringing all of `main` into a release branch. That is not what you want for a hotfix. When a fix has already merged to `main` and needs to ship on an existing release line, cherry-pick just that commit instead.

1. Start a branch from the release branch you are patching (not from `main`):
   ```bash
   git fetch origin
   git checkout -b <you>/backport-<pr>-to-<major>.<minor> "origin/release/v<major>.<minor>"
   ```

2. Cherry-pick the fix. Use `-x` so the commit records where it came from:
   ```bash
   git cherry-pick -x <sha-on-main>
   ```

   PRs are squash-merged into `main`, so each merged PR is a single ordinary commit and a plain `cherry-pick` works. Find it by PR number:
   ```bash
   git log origin/main --oneline --grep "(#<pr>)"
   ```

   If you are ever picking an actual merge commit, add `-m 1` to pick its change relative to the first parent. To tell the two apart, `git rev-list --parents -n 1 <sha>` prints the commit followed by its parents: two entries is an ordinary commit, three or more is a merge.

3. Set the version for the release. For a stable line, edit `version.json` to the next patch version. For a preview line, adjust `versionHeightOffset` instead. See [Preview releases](#preview-releases).

4. Push and open a PR against the release branch.

5. Verify the version **before** publishing, then follow [Publishing](#publishing) as usual.

Keep backport PRs to the fix itself. Sweeping in unrelated commits from `main` turns a hotfix into an untested release.

> [!IMPORTANT]
> Unlike PRs into `main`, backport PRs must be merged with a **merge commit**, not a squash. On a preview line the version number is derived from commit height, so squashing changes the resulting version. See [Preview releases](#preview-releases).

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
| `release/v2.0` | `microsoft_teams_apps-2.0.16.tar.gz` |
| `release/v2.1` | `microsoft_teams_apps-2.1.0a2.tar.gz` |

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

### Preview releases

A preview line keeps `{height}` in the version string and lets Nerdbank.GitVersioning number each release, for example `release/v2.1`:

```json
{
  "version": "2.1.0-alpha.{height}",
  "versionHeightOffset": -14
}
```

The published version is `height + versionHeightOffset`. Three rules govern the height:

- Height **resets** when the `version` string itself changes.
- Editing `versionHeightOffset` does **not** reset it.
- Height is `1 + max(height of each parent)`, so every commit you add, **including the merge commit**, increases it.

That last point is the one that bites. A backport adds the cherry-pick, plus a commit editing `version.json`, plus the merge commit itself. To land on a chosen alpha number:

```
versionHeightOffset = target_alpha - height_of_the_final_merge_commit
```

Worked example, backporting one fix onto `release/v2.1` to produce `2.1.0-alpha.2`:

| Step | Height |
|------|--------|
| release branch tip before the backport | 13 |
| + cherry-picked fix | 14 |
| + commit editing `versionHeightOffset` | 15 |
| + merge commit | **16** |

So the offset is `2 - 16 = -14`.

This is why preview backports must be merged with a **merge commit**. Squashing removes commits from the chain, the final height is lower than planned, and the pipeline republishes a version number that is already on PyPI.

Because the offset depends on the merge commit that does not exist yet, verify after merging and before publishing:

```bash
git checkout "release/v<major>.<minor>" && git pull
nbgv get-version -v SemVer2
```

If the number is wrong, correct `versionHeightOffset` and re-check. A corrective commit adds height of its own, so recompute rather than assuming the difference.

> [!TIP]
> You can confirm the number before merging by simulating the merge locally. `publicReleaseRefSpec` matches on branch name, so the local branch has to be named like the real one:
> ```bash
> git checkout -b "release/v<major>.<minor>" "origin/release/v<major>.<minor>"
> git merge --no-ff <your-backport-branch>
> nbgv get-version -v SemVer2   # should print the version you intend to publish
> ```
> Delete the local branch afterwards so it cannot be pushed by accident.

### After a release

Leave `version.json` alone once a release ships. A stable branch keeps its literal version, so the next release PR has to bump it; a preview branch increments `{height}` on its own and needs nothing.

Sitting on an already-published stable version is deliberate: PyPI rejecting the re-upload is the only guard against an accidental publish, and a `-dev` version would publish cleanly instead.

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

Before triggering a **Public** run, confirm the version the branch will actually produce:

```bash
git checkout "release/v<major>.<minor>" && git pull
nbgv get-version -v SemVer2
```

PyPI rejects re-uploading a version that already exists, so a wrong number here means a failed publish, or worse, a silently skipped version. This matters most on preview lines, where the number is computed rather than written down.

### After publishing

Confirm the packages landed as intended. Every package in the workspace is published together, so check more than one:

```bash
pip index versions microsoft-teams-apps --pre
```

A preview release should leave the `latest` tag alone. An unpinned `pip install microsoft-teams-apps` should still resolve to the newest **stable** version, while `pip install microsoft-teams-apps==<preview-version>` gets the preview.

## Tagging and GitHub Release

After the publish pipeline finishes and packages land on PyPI, tag the release and create a GitHub Release page:

```bash
# Create a draft release at the matching release branch tip
gh release create v<version> -R microsoft/teams.py \
  --target "release/v<major>.<minor>" --title "v<version>" --draft \
  --generate-notes --notes-start-tag v<previous-version>
```

Add `--prerelease` for preview releases so GitHub does not present them as the latest stable version.

**Note:** GitHub's auto-generated notes walk back from the release branch tip, so they tend to list only the release or backport PR rather than the changes a reader cares about. Rewrite the body to describe the actual change, and credit the reporter when a fix came from an outside bug report. For a release cut from `main`, you can pull the real PR delta by date:

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
