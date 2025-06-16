from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class NotificationInfo(BaseModel):
    """
    Specifies if a notification is to be sent for the mentions.
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    alert: Optional[bool] = Field(None, description="true if notification is to be sent to the user, false otherwise.")
    alert_in_meeting: Optional[bool] = Field(
        None,
        description="true if a notification is to be shown to the user while in a meeting, false otherwise.",
    )
    external_resource_url: Optional[str] = Field(
        None,
        description="the value of the notification's external resource url",
    )
