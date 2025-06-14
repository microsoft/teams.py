"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ConversationResource(BaseModel):
    """Resource returned when creating a conversation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    id: str = Field(..., description="The ID of the created conversation")
    activity_id: str = Field(..., description="The ID of the activity that created the conversation")
    service_url: str = Field(..., description="The service URL for the conversation")
