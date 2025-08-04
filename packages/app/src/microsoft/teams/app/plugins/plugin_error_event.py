"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional

from microsoft.teams.api import Activity

if TYPE_CHECKING:
    from .plugin import Plugin


class PluginErrorEvent(NamedTuple):
    """Event emitted when an error occurs."""

    sender: Optional["Plugin"]
    """The sender"""

    error: Exception
    """The error"""

    activity: Optional[Activity] | Dict[str, Any]
    """The activity"""
