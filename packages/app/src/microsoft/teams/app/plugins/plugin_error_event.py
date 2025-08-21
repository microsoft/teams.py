"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, NamedTuple, Optional

from microsoft.teams.api import Activity

if TYPE_CHECKING:
    from .plugin_base import PluginBase


class PluginErrorEvent(NamedTuple):
    """Event emitted when an error occurs."""

    error: Exception
    """The error"""

    sender: Optional["PluginBase"] = None
    """The sender"""

    activity: Optional[Activity] = None
    """The activity"""
