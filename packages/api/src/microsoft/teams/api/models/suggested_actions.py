"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List

from .card import CardAction
from .custom_base_model import CustomBaseModel


class SuggestedActions(CustomBaseModel):
    """Actions that can be suggested to users."""

    to: List[str]
    """
    Ids of the recipients that the actions should be shown to.  These Ids are relative to the
    channelId and a subset of all recipients of the activity
    """

    actions: List[CardAction]
    """Actions that can be shown to the user."""
