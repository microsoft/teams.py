#!/usr/bin/env python3

"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_command(cmd: list[str], cwd: Optional[str] = None) -> None:
    """Run a command and raise an exception if it fails."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Error output: {result.stderr}")
        sys.exit(1)


def create_package(package_name: str) -> None:
    """Create a new package with the specified name."""
    # Convert package name to lowercase for directory name
    package_dir = package_name.lower()
    package_path = Path("packages") / package_dir
    full_package_name = f"microsoft-teams-{package_name.lower()}"

    if package_path.exists():
        print(f"Error: Package directory {package_path} already exists")
        sys.exit(1)

    # Step 1: Run uv init
    print(f"Creating new package {package_name}...")
    run_command(["uv", "init", "--lib", str(package_path), "--author-from", "none"])

    # Step 2: Move and restructure the source directory
    src_dir = package_path / "src"
    original_package_dir = src_dir / package_name
    target_dir = src_dir / "microsoft" / "teams" / package_name.lower()

    # Create the new directory structure
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    # Move the package directory
    if original_package_dir.exists():
        shutil.move(str(original_package_dir), str(target_dir))

    # Step 3 & 4: Update pyproject.toml
    pyproject_path = package_path / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path, "r") as f:
            content = f.read()

        # Update package name
        content = content.replace(f'name = "{package_name}"', f'name = "{full_package_name}"')

        if "repository = " not in content:
            content += '\nrepository = "https://github.com/microsoft/teams.py"\n'

        if "keywords = [" not in content:
            content += '\nkeywords = ["microsoft", "teams", "ai", "bot", "agents"]\n'

        if "license = " not in content:
            content += '\nlicense = "MIT"\n'

        # Add authors field if not present
        if "authors = [" not in content:
            content = content.replace(
                'description = "Add your description here"',
                'description = "Add your description here"\nauthors = [{ name = "Microsoft", email = "teams@microsoft.com" }]',  # noqa: E501
            )

        # Add wheel build configuration
        if "[tool.hatch.build.targets.wheel]" not in content:
            content += '\n[tool.hatch.build.targets.wheel]\npackages = ["src/microsoft"]\n'

        with open(pyproject_path, "w") as f:
            f.write(content)

    # Step 5: Update root pyproject.toml
    root_pyproject_path = Path("pyproject.toml")
    if root_pyproject_path.exists():
        with open(root_pyproject_path, "r") as f:
            content = f.read()

        # Add the new package to uv.sources if not already present
        source_entry = f'"{full_package_name}" = {{ workspace = true }}'
        if source_entry not in content:
            # Find the [tool.uv.sources] section
            if "[tool.uv.sources]" in content:
                # Add the new source after the section header
                content = content.replace("[tool.uv.sources]", f"[tool.uv.sources]\n{source_entry}")
            else:
                # Add the entire section if it doesn't exist
                content += f"\n[tool.uv.sources]\n{source_entry}\n"

        with open(root_pyproject_path, "w") as f:
            f.write(content)

    print(f"\nPackage {package_name} created successfully!")
    print(f"Location: {package_path}")
    print("\nNext steps:")
    print("1. Add your package code in src/microsoft/teams/{package_name.lower()}")
    print("2. Update the package description in pyproject.toml")
    print("3. Add any required dependencies to pyproject.toml")


def main():
    parser = argparse.ArgumentParser(description="Create a new package in the teams.py project")
    parser.add_argument("package_name", help="Name of the package to create")
    args = parser.parse_args()

    create_package(args.package_name)


if __name__ == "__main__":
    main()
