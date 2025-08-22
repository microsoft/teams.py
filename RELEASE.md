# Release steps

1. Run `uv run scripts/release.py <bump_type>`
2. This should bump all the versions for the packages and also created a release branch.
3. Create a PR and get it merged.
4. Now go to https://github.com/microsoft/teams.py/releases/new and create a new release.
5. This will automatically kick off a release workflow that needs to be aproved.
6. Once approved, the release will be published to PyPI.