"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, NamedTuple

from microsoft.teams.api.models import SentActivity

if TYPE_CHECKING:
    from .sender import Sender


class PluginActivitySentEvent(NamedTuple):
    """Event emitted by a plugin when an activity is sent."""

    sender: "Sender"
    """The sender of the activity"""

    activity: SentActivity
    """The sent activity"""
