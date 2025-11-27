"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import warnings


def test_old_import_shows_deprecation_warning():
    """Old imports work but show DeprecationWarning"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from microsoft.teams.common import ConsoleLogger

        assert len(w) >= 1
        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert "deprecated" in str(w[0].message).lower()
        assert ConsoleLogger is not None


def test_new_import_no_warning():
    """New imports work without warnings"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from microsoft_teams.common import ConsoleLogger

        # No warnings expected
        assert len(w) == 0
        assert ConsoleLogger is not None


def test_both_namespaces_same_class():
    """Old and new imports reference the same class"""
    from microsoft.teams.common import ConsoleLogger as OldLogger
    from microsoft_teams.common import ConsoleLogger as NewLogger

    assert OldLogger is NewLogger
    assert id(OldLogger) == id(NewLogger)
