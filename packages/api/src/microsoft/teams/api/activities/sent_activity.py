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

    @classmethod
    def merge(cls, activity_params: ActivityParams, curr_activity: "SentActivity") -> "SentActivity":
        merged_data = {**activity_params.model_dump(), **curr_activity.model_dump()}
        return cls(**merged_data)
