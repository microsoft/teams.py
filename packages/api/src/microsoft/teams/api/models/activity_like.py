"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from microsoft.teams.cards.adaptive_card import AdaptiveCard

from ..clients import ActivityParams
from .custom_base_model import CustomBaseModel

ActivityLike = Union[ActivityParams, str, AdaptiveCard]


class SentActivity(ActivityParams, CustomBaseModel):
    """Represents an activity that has been sent."""

    id: str
