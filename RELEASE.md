# Release steps

1. Run `uv run scripts/release.py <bump_type>`. See [Bump types](#bump-types) for available options.
2. This should bump all the versions for the packages and also created a release branch.
3. Create a PR and get it merged.
4. Now go to https://github.com/microsoft/teams.py/releases/new and create a new release.
5. This will automatically kick off a release workflow that needs to be aproved.
6. Once approved, the release will be published to PyPI.

## Appendix

# Bump types
Version bump types:
  major    - Increment major version (1.0.0 -> 2.0.0)
  minor    - Increment minor version (1.0.0 -> 1.1.0)
  patch    - Increment patch version (1.0.0 -> 1.0.1)
  stable   - Remove pre-release suffix (1.0.0a1 -> 1.0.0)
  alpha    - Add/increment alpha pre-release (1.0.0 -> 1.0.0a1)
  beta     - Add/increment beta pre-release (1.0.0 -> 1.0.0b1)
  rc       - Add/increment release candidate (1.0.0 -> 1.0.0rc1)
  post     - Add/increment post-release (1.0.0 -> 1.0.0.post1)
  dev      - Add/increment dev release (1.0.0 -> 1.0.0.dev1)
 