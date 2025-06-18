"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


# TODO: This is a barebones model for now.
class Activity(BaseModel):
    """Represents a Teams activity."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    type: str = "message"
    """
    The type of activity (e.g. 'message').
    """
    text: Optional[str] = None
    """
    The text content of the activity.
    """
    reply_to_id: Optional[str] = None
    """
    The ID of the activity this is replying to.
    """
    properties: Optional[Dict[str, Any]] = None
