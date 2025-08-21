#!/usr/bin/env python3
"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Dict, List

"""
Release script for Microsoft Teams Python SDK.
Handles version bumping across all packages and optionally creates release branches.
"""


def get_packages_dir() -> Path:
    """Get the packages directory relative to the script location."""
    script_dir = Path(__file__).parent
    return script_dir.parent / "packages"


def find_packages() -> List[Path]:
    """Find all package directories containing pyproject.toml."""
    packages_dir = get_packages_dir()
    packages: List[Path] = []

    for item in packages_dir.iterdir():
        if item.is_dir() and (item / "pyproject.toml").exists():
            packages.append(item)

    return sorted(packages)


def bump_package_version(package_path: Path, bump_type: str) -> str:
    """Bump the version of a package and return the new version."""
    print(f"Bumping {package_path.name} version ({bump_type})...")

    try:
        result = subprocess.run(
            ["uv", "version", "--bump", bump_type], cwd=package_path, capture_output=True, text=True, check=True
        )
        print(f"  ✓ {package_path.name}: {result.stdout.strip()}")
        return get_package_version(package_path)
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to bump {package_path.name}: {e.stderr}")
        sys.exit(1)


def get_package_version(package_path: Path) -> str:
    """Extract version from pyproject.toml."""
    pyproject_path = package_path / "pyproject.toml"

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except (KeyError, tomllib.TOMLDecodeError, OSError) as e:
        print(f"Error reading version from {pyproject_path}: {e}")
        sys.exit(1)


def create_release_branch(version: str) -> str:
    """Create a new release branch."""
    branch_name = f"release_{version}"

    try:
        # Create and switch to new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        print(f"Created and switched to branch: {branch_name}")

        # Add all changes
        subprocess.run(["git", "add", "."], check=True)

        # Commit changes
        subprocess.run(["git", "commit", "-m", f"Release version {version}"], check=True)
        print(f"Committed changes for release {version}")

        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Error creating release branch: {e}")
        sys.exit(1)


def create_pull_request(branch_name: str, version: str) -> None:
    """Create a pull request for the release."""
    try:
        # Push the branch
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True, capture_output=True)
        print(f"Pushed branch {branch_name} to origin")

        # Create PR using gh CLI
        pr_title = f"Release version {version}"
        pr_body = f"""## Release {version}

This PR contains version bumps for all packages to {version}.

### Changes
- Bumped all package versions to {version}

### Checklist
- [ ] All tests pass
- [ ] Documentation updated if needed
- [ ] Ready for release

🤖 Generated with release script"""

        subprocess.run(
            ["gh", "pr", "create", "--title", pr_title, "--body", pr_body, "--base", "main"],
            check=True,
            capture_output=True,
        )

        print(f"✓ Created pull request: {pr_title}")

    except subprocess.CalledProcessError as e:
        print(f"Error creating pull request: {e}")
        print("You can manually push the branch and create a PR:")
        print(f"  git push -u origin {branch_name}")


def main() -> None:
    """Main script entry point."""
    parser = argparse.ArgumentParser(
        description="Release script for Microsoft Teams Python SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
        """,
    )

    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch", "stable", "alpha", "beta", "rc", "post", "dev"],
        help="Type of version bump to perform",
    )

    args = parser.parse_args()

    # Find all packages
    packages = find_packages()
    if not packages:
        print("No packages found in packages/ directory")
        sys.exit(1)

    print(f"Found {len(packages)} packages:")
    for pkg in packages:
        print(f"  - {pkg.name}")
    print()

    # Bump versions for all packages
    versions: Dict[str, str] = {}
    for package in packages:
        new_version = bump_package_version(package, args.bump_type)
        versions[package.name] = new_version

    # All packages should have the same version
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        print("Warning: Packages have different versions after bump:")
        for pkg, ver in versions.items():
            print(f"  {pkg}: {ver}")

    # Use the first version as the release version
    release_version = next(iter(unique_versions))
    print(f"\nAll packages bumped to version: {release_version}")

    # Ask user about creating branch and PR
    response = input("\nWould you like to create a release branch and PR? (y/N): ").strip().lower()

    if response in ("y", "yes"):
        branch_name = create_release_branch(release_version)
        create_pull_request(branch_name, release_version)
        print(f"\n✓ Release {release_version} is ready!")
        print(f"  Branch: {branch_name}")
        print("  Pull request created")
    else:
        print(f"\nVersion bump complete. Release version: {release_version}")
        print("You can manually commit and create a branch/PR when ready.")


if __name__ == "__main__":
    main()
