"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..models import CustomBaseModel
from . import ActivityParams


class SentActivity(CustomBaseModel):
    """Represents an activity that was sent."""

    id: str
    """Id of the activity."""

    activity_params: ActivityParams
    """Additional parameters for the activity."""
