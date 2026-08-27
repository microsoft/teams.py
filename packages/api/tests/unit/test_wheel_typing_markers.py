"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import subprocess
from pathlib import Path
from zipfile import ZipFile

PACKAGE_MARKERS = {
    "microsoft_teams_api": "microsoft_teams/api/py.typed",
    "microsoft_teams_apps": "microsoft_teams/apps/py.typed",
    "microsoft_teams_botbuilder": "microsoft_teams/botbuilder/py.typed",
    "microsoft_teams_cards": "microsoft_teams/cards/py.typed",
    "microsoft_teams_common": "microsoft_teams/common/py.typed",
    "microsoft_teams_graph": "microsoft_teams/graph/py.typed",
    "microsoft_teams_m365extensions": "microsoft_teams/m365extensions/py.typed",
}


def test_built_wheels_include_typing_markers(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[4]
    subprocess.run(
        ["uv", "build", "--all-packages", "--wheel", "--out-dir", str(tmp_path)],
        cwd=repository_root,
        check=True,
    )

    wheels = list(tmp_path.glob("*.whl"))
    for distribution, marker in PACKAGE_MARKERS.items():
        matching_wheels = [wheel for wheel in wheels if wheel.name.startswith(f"{distribution}-")]
        assert len(matching_wheels) == 1, f"Expected one wheel for {distribution}, found {matching_wheels}"

        with ZipFile(matching_wheels[0]) as archive:
            assert marker in archive.namelist(), f"{matching_wheels[0].name} is missing {marker}"
