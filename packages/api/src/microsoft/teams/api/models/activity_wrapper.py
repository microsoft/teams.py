"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any

from ..activities import Activity
from .custom_base_model import CustomBaseModel


class ActivityWrapper(CustomBaseModel):
    """Wrapper model for validating discriminated union activities"""

    activity: Activity

    @classmethod
    def validate_activity(cls, data: dict[str, Any]) -> Activity:
        """Helper method to validate and extract activity"""
        wrapper = cls.model_validate({"activity": data})
        return wrapper.activity
