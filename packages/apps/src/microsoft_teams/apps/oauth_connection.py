"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

# One definition of what an OAuth connection name is, shared by the registry, the
# pending-state keys and the callback handlers so they can never disagree about
# whether two spellings mean the same connection.
#
# Names are compared case-insensitively but stored with the casing the app
# registered, because that casing is what the Token Service and the Azure Bot
# configuration display. Surrounding whitespace is never significant: it is
# almost always a copy-paste artefact from the portal, and treating "graph" and
# "graph " as different connections silently breaks routing.
#
# ``lower()`` rather than ``casefold()`` is deliberate. It matches the existing
# stored keys and the other SDKs, so a name that round-tripped through another
# implementation still resolves here.


def normalize_connection_name(connection_name: str) -> str:
    """Return the connection name with surrounding whitespace removed.

    Args:
        connection_name: The name as supplied by the app.

    Returns:
        The trimmed name, preserving its original casing.

    Raises:
        ValueError: if it is empty or only whitespace. A blank connection name
            cannot address anything, so accepting one only defers the failure
            to a confusing Token Service error later.
    """
    normalized = connection_name.strip()
    if not normalized:
        raise ValueError("OAuth connection name must not be blank.")
    return normalized


def connection_lookup_key(connection_name: Any) -> Optional[str]:
    """Return the case-insensitive key for a connection name, or ``None``.

    Lookups are deliberately lenient where registration is strict: a blank or
    non-string name simply matches nothing, so ``Mapping`` semantics such as
    ``registry.get(name)`` returning ``None`` and ``name in registry`` being
    ``False`` keep working instead of raising.
    """
    if not isinstance(connection_name, str):
        return None
    normalized = connection_name.strip()
    return normalized.lower() if normalized else None
