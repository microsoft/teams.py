"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from .custom_base_model import CustomBaseModel


# TODO: This is a barebones model for now.
class Activity(CustomBaseModel):
    """Represents a Teams activity."""

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
