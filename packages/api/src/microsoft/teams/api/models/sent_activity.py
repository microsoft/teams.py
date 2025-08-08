"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..clients.conversation.activity import ActivityParams
from .custom_base_model import CustomBaseModel


class SentActivity(CustomBaseModel):
    """Represents an activity that was sent."""

    id: str
    """Id of the activity."""

    activity_params: Optional[ActivityParams] = None
