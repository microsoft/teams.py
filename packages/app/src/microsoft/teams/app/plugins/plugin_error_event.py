"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, Optional

from microsoft.teams.api import Activity, CustomBaseModel

if TYPE_CHECKING:
    from .plugin_base import PluginBase


class PluginErrorEvent(CustomBaseModel):
    """Event emitted when an error occurs."""

    sender: Optional["PluginBase"] = None
    """The sender"""

    error: Exception
    """The error"""

    activity: Optional[Activity]
    """The activity"""
