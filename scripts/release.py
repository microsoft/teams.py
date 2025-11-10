#!/usr/bin/env python3
"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import tomllib


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


def dry_run_version_bump(package_path: Path, bump_types: List[str]) -> str:
    """Run a dry-run version bump to see what the new version would be.

    Accepts one or more bump types and passes multiple --bump flags to `uv`.
    """
    try:
        cmd = ["uv", "version"]
        for bt in bump_types:
            cmd.extend(["--bump", bt])
        cmd.append("--dry-run")

        result = subprocess.run(
            cmd,
            cwd=package_path,
            capture_output=True,
            text=True,
            check=True,
        )
        # Extract the version from the output
        # Handle multiple formats:
        # Format 1: "Would bump version from X.Y.Z to A.B.C"
        # Format 2: "package-name X.Y.Z => A.B.C"
        # Format 3: Just "A.B.C"
        output = result.stdout.strip()

        if " to " in output:
            return output.split(" to ")[-1]
        elif " => " in output:
            return output.split(" => ")[-1]
        else:
            # Fallback: extract version from the end of the output
            return output.split()[-1]
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to dry-run bump {package_path.name}: {e.stderr}")
        sys.exit(1)


def bump_package_version(package_path: Path, bump_types: List[str], verbose: bool = False) -> str:
    """Bump the version of a package and return the new version.

    Accepts one or more bump types and passes multiple --bump flags to `uv`.
    """
    print(f"Bumping {package_path.name} version ({', '.join(bump_types)})...")

    try:
        cmd = ["uv", "version"]
        for bt in bump_types:
            cmd.extend(["--bump", bt])

        result = subprocess.run(
            cmd,
            cwd=package_path,
            capture_output=not verbose,
            text=True,
            check=True,
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


def get_last_tag() -> str:
    """Get the last git tag matching v* pattern."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "--match", "v*"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Warning: No previous tags found matching 'v*' pattern")
        return ""


def get_commits_since_tag(tag: str) -> List[str]:
    """Get commit messages from current HEAD to the specified tag."""
    try:
        # Get commit messages in format: "- <commit message>"
        result = subprocess.run(
            ["git", "log", f"{tag}..HEAD", "--pretty=format:- %s"],
            capture_output=True,
            text=True,
            check=True,
        )
        commits = result.stdout.strip().split("\n")
        return [c for c in commits if c]  # Filter empty strings
    except subprocess.CalledProcessError as e:
        print(f"Error getting commits: {e}")
        return []


def create_release_branch(version: str, verbose: bool = False) -> str:
    """Create a new release branch."""
    branch_name = f"release_{version}"

    try:
        # Create and switch to new branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=not verbose)
        print(f"Created and switched to branch: {branch_name}")

        # Add all changes
        subprocess.run(["git", "add", "."], check=True, capture_output=not verbose)

        # Commit changes
        subprocess.run(["git", "commit", "-m", f"Release version {version}"], check=True, capture_output=not verbose)
        print(f"Committed changes for release {version}")

        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Error creating release branch: {e}")
        sys.exit(1)


def create_pull_request(version: str, commits: List[str], verbose: bool = False) -> None:
    """Create a pull request for the release."""
    try:
        # Push the branch to remote
        branch_name = f"release_{version}"
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            check=True,
            capture_output=not verbose,
        )
        print(f"Pushed branch {branch_name} to remote")

        # Create PR body with commits
        pr_body = f"## Release {version}\n\n### Changes\n\n"
        if commits:
            pr_body += "\n".join(commits)
        else:
            pr_body += "No commits since last tag"

        # Create PR using gh CLI
        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"Release {version}",
                "--body",
                pr_body,
                "--base",
                "main",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print("✓ Pull request created successfully")
        print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error creating pull request: {e}")
        if e.stderr:
            print(f"  {e.stderr}")
        sys.exit(1)


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
        "bump_types",
        nargs="+",
        choices=["major", "minor", "patch", "stable", "alpha", "beta", "rc", "post", "dev"],
        help=(
            "One or two bump types to perform (e.g. 'major' or 'major alpha'). "
            "If two are provided, the second will be passed as an additional --bump to uv."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output from commands",
    )

    args = parser.parse_args()

    # Validate that at most two bump types were provided
    if len(args.bump_types) > 2:
        print("Error: Provide at most two bump types (e.g. 'major' or 'major alpha').")
        sys.exit(1)

    # Find all packages
    packages = find_packages()
    if not packages:
        print("No packages found in packages/ directory")
        sys.exit(1)

    print(f"Found {len(packages)} packages:")
    for pkg in packages:
        print(f"  - {pkg.name}")
    print()

    # Get commits since last tag for PR description (show regardless of PR creation)
    last_tag = get_last_tag()
    commits_since_tag: List[str] = []
    if last_tag:
        print(f"Last tag: {last_tag}")
        commits_since_tag = get_commits_since_tag(last_tag)
        if commits_since_tag:
            print(f"\nCommits since {last_tag}:")
            for commit in commits_since_tag:
                print(f"  {commit}")
            print()
        else:
            print(f"No commits since {last_tag}\n")
    else:
        print("No previous tags found\n")

    # First, do a dry-run to check all packages would have the same version
    print("Running dry-run to check version consistency...")
    dry_run_versions: Dict[str, str] = {}
    for package in packages:
        new_version = dry_run_version_bump(package, args.bump_types)
        dry_run_versions[package.name] = new_version
        print(f"  {package.name}: {get_package_version(package)} -> {new_version}")

    # Check if all packages would have the same version
    unique_dry_run_versions = set(dry_run_versions.values())
    if len(unique_dry_run_versions) != 1:
        print("\n❌ ERROR: Packages would have different versions after bump:")
        for pkg, ver in dry_run_versions.items():
            print(f"  {pkg}: {ver}")
        print("\nAll packages must have the same version. Please fix version inconsistencies first.")
        sys.exit(1)

    target_version = next(iter(unique_dry_run_versions))
    print(f"\n✓ All packages will be bumped to: {target_version}")
    print("\nProceeding with actual version bump...")

    # Now do the actual version bump
    versions: Dict[str, str] = {}
    for package in packages:
        new_version = bump_package_version(package, args.bump_types, args.verbose)
        versions[package.name] = new_version

    # Verify all packages have the same version (should always pass now)
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        print("❌ CRITICAL ERROR: Packages have different versions after bump (this should not happen):")
        for pkg, ver in versions.items():
            print(f"  {pkg}: {ver}")
        sys.exit(1)

    # Use the first version as the release version
    release_version = next(iter(unique_versions))
    print(f"\nAll packages bumped to version: {release_version}")

    # Ask user about creating branch
    response = input("\nWould you like to create a release branch (y/N): ").strip().lower()

    if response in ("y", "yes"):
        branch_name = create_release_branch(release_version, args.verbose)
        print(f"\n✓ Release {release_version} is ready!")
        print(f"  Branch: {branch_name}")

        # Ask user about creating PR
        pr_response = input("\nWould you like to create a pull request (y/N): ").strip().lower()
        if pr_response in ("y", "yes"):
            create_pull_request(release_version, commits_since_tag, args.verbose)
        else:
            print("\nYou can manually create a PR when ready using:")
            print(f"  git push -u origin {branch_name}")
            print(f"  gh pr create --title 'Release {release_version}' --base main")
            # Show commits again for easy copy-paste
            if commits_since_tag:
                print("\nCommits to include in PR description:")
                for commit in commits_since_tag:
                    print(f"  {commit}")
    else:
        print(f"\nVersion bump complete. Release version: {release_version}")
        print("You can manually commit and create a branch/PR when ready.")
        # Show commits for reference even if no branch was created
        if commits_since_tag:
            print("\nCommits since last tag:")
            for commit in commits_since_tag:
                print(f"  {commit}")


if __name__ == "__main__":
    main()
