from typing import Optional

from pydantic import BaseModel, Field


class NotificationInfo(BaseModel):
    """
    Specifies if a notification is to be sent for the mentions.
    """

    alert: Optional[bool] = Field(None, description="true if notification is to be sent to the user, false otherwise.")
    alert_in_meeting: Optional[bool] = Field(
        None,
        description="true if a notification is to be shown to the user while in a meeting, false otherwise.",
        alias="alertInMeeting",
    )
    external_resource_url: Optional[str] = Field(
        None, description="the value of the notification's external resource url", alias="externalResourceUrl"
    )
