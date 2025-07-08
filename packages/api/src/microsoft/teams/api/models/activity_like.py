"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from microsoft.teams.cards import AdaptiveCard

from ..activities import ActivityParams
from .custom_base_model import CustomBaseModel

ActivityLike = Union[ActivityParams, str, AdaptiveCard]
"""Represents anything that can be transformed into an activity in an automated way."""


class SentActivity(CustomBaseModel):
    """
    Represents an activity that was sent.
    """

    id: str
    activity: ActivityParams
