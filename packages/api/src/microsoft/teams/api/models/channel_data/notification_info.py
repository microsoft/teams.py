"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class NotificationInfo(CustomBaseModel):
    """
    Specifies if a notification is to be sent for the mentions.
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    alert: Optional[bool] = None
    "true if notification is to be sent to the user, false otherwise."

    alert_in_meeting: Optional[bool] = None
    "true if a notification is to be shown to the user while in a meeting, false otherwise."

    external_resource_url: Optional[str] = None
    "the value of the notification's external resource url"
