"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Activity(BaseModel):
    """
    Represents a Teams activity/message in a conversation.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    type: str = Field("message", description="The type of activity (e.g. 'message')")
    text: Optional[str] = Field(None, description="The text content of the activity")
    reply_to_id: Optional[str] = Field(None, description="The ID of the activity this is replying to")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties for the activity")
