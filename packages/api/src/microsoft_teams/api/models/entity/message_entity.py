"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from ..custom_base_model import CustomBaseModel


class MessageEntity(CustomBaseModel):
    """
    Base message entity following schema.org Message schema
    """

    type: Literal["https://schema.org/Message"] = "https://schema.org/Message"

    at_type: Literal["Message"] = "Message"
    "Required as default value"

    at_context: Literal["https://schema.org"] = "https://schema.org"
    "Required as default value"

    at_id: Literal[""] = ""
    "Must be left blank. This is for the Bot Framework schema"

    additional_type: Optional[List[str]] = None
    "Additional contnet type tags"
