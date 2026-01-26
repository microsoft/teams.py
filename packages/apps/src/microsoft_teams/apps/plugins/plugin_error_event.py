"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import NamedTuple, Optional

from microsoft_teams.api import Activity


class PluginErrorEvent(NamedTuple):
    """Event emitted when an error occurs."""

    error: Exception
    """The error"""

    activity: Optional[Activity] = None
    """The activity"""
