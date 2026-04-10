"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import patch

from hatch_teams_build.metadata_hook import TeamsBuildMetadataHook, _add_version_constraint, _strip_local


class TestStripLocal:
    def test_strips_local_segment(self):
        assert _strip_local("2.0.0a46+gf235eb85") == "2.0.0a46"

    def test_no_local_segment(self):
        assert _strip_local("2.0.0a46") == "2.0.0a46"

    def test_stable_version(self):
        assert _strip_local("2.0.0") == "2.0.0"


class TestAddVersionConstraint:
    def test_bare_workspace_dep(self):
        assert _add_version_constraint("microsoft-teams-common", "2.0.0a46") == "microsoft-teams-common>=2.0.0a46"

    def test_bare_workspace_dep_with_whitespace(self):
        assert _add_version_constraint("  microsoft-teams-api  ", "2.0.0a46") == "microsoft-teams-api>=2.0.0a46"

    def test_already_constrained_dep(self):
        assert _add_version_constraint("microsoft-teams-common>=1.0.0", "2.0.0a46") == "microsoft-teams-common>=1.0.0"

    def test_non_workspace_dep(self):
        assert _add_version_constraint("fastapi>=0.115.13", "2.0.0a46") == "fastapi>=0.115.13"

    def test_bare_non_workspace_dep(self):
        assert _add_version_constraint("python-dotenv", "2.0.0a46") == "python-dotenv"

    def test_dep_with_extras(self):
        assert _add_version_constraint("pyjwt[crypto]>=2.12.0", "2.0.0a46") == "pyjwt[crypto]>=2.12.0"


class TestMetadataHookFallback:
    def _run_update(self, version: str, metadata: dict):
        """Run TeamsBuildMetadataHook.update with a mocked version source."""
        with patch("hatch_teams_build.metadata_hook.TeamsBuildVersionSource") as mock_cls:
            mock_cls.return_value.get_version_data.return_value = {"version": version}
            hook = TeamsBuildMetadataHook(".", {})
            hook.update(metadata)

    def test_skips_rewrite_when_nbgv_unavailable(self):
        """When nbgv is not available (version 0.0.0), deps should be left unchanged."""
        metadata = {
            "dependencies": ["microsoft-teams-common", "fastapi>=0.115.13"],
            "optional-dependencies": {"graph": ["microsoft-teams-graph"]},
        }
        original_deps = list(metadata["dependencies"])
        original_optional = {"graph": list(metadata["optional-dependencies"]["graph"])}

        self._run_update("0.0.0", metadata)

        assert metadata["dependencies"] == original_deps
        assert metadata["optional-dependencies"] == original_optional

    def test_rewrites_deps_when_nbgv_available(self):
        """When nbgv provides a real version, deps should be rewritten."""
        metadata = {
            "dependencies": ["microsoft-teams-common", "fastapi>=0.115.13"],
        }

        self._run_update("2.0.0a48+gabcdef", metadata)

        assert metadata["dependencies"] == ["microsoft-teams-common>=2.0.0a48", "fastapi>=0.115.13"]
