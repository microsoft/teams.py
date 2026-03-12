"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings


def test_old_import_shows_deprecation_warning():
    """Old imports work but show DeprecationWarning"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from microsoft.teams.common import Client

        assert len(w) >= 1
        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert "deprecated" in str(w[0].message).lower()
        assert Client is not None


def test_new_import_no_warning():
    """New imports work without warnings"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from microsoft_teams.common import Client

        # No warnings expected
        assert len(w) == 0
        assert Client is not None


def test_both_namespaces_same_class():
    """Old and new imports reference the same class"""
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")

        from microsoft.teams.common import Client as OldClient
        from microsoft_teams.common import Client as NewClient

        assert OldClient is NewClient
        assert id(OldClient) == id(NewClient)


def test_new_import_from_submodule():
    """New imports work for submodules without warnings"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from microsoft_teams.common.http import Client

        # No warnings expected
        assert len(w) == 0
        assert Client is not None


def test_deprecation_warning_message_content():
    """Verify deprecation warning contains useful information"""
    # Need to import in a fresh module context to ensure warning fires
    import sys

    # Remove the module if it was already imported
    if "microsoft.teams.common" in sys.modules:
        del sys.modules["microsoft.teams.common"]
    if "microsoft.teams" in sys.modules:
        del sys.modules["microsoft.teams"]

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from microsoft.teams.common import ConsoleLogger  # noqa: F401

        assert len(w) >= 1, f"Expected deprecation warning, got {len(w)} warnings"
        warning_msg = str(w[0].message)

        # Should mention the old namespace
        assert "microsoft.teams.common" in warning_msg

        # Should mention the new namespace
        assert "microsoft_teams.common" in warning_msg

        # Should mention version when it will be removed
        assert "2.0.0" in warning_msg

        # Should indicate it's deprecated
        assert "deprecated" in warning_msg.lower()


def test_old_namespace_exports_all():
    """Old namespace exports all classes from new namespace"""
    from microsoft.teams.common import Client, ConsoleLogger, EventEmitter

    # All exports should work
    assert ConsoleLogger is not None
    assert Client is not None
    assert EventEmitter is not None
