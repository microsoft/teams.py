"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any

from pydantic import BaseModel

from . import Activity


class ActivityWrapper(BaseModel):
    """Wrapper model for validating discriminated union activities"""

    activity: Activity

    @classmethod
    def validate_activity(cls, data: dict[str, Any]) -> Activity:
        """Helper method to validate and extract activity"""
        wrapper = cls.model_validate({"activity": data})
        return wrapper.activity
