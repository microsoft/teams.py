"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, NamedTuple

from microsoft.teams.api import Activity, TokenProtocol

if TYPE_CHECKING:
    from .sender import Sender


class PluginActivityEvent(NamedTuple):
    """Event emitted by a plugin when an activity is received."""

    sender: "Sender"
    """The sender"""

    token: TokenProtocol
    """Inbound request token"""

    activity: Activity
    """Inbound request activity payload"""
