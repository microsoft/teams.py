"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel


class MessageBody(CustomBaseModel):
    """
    Plaintext/HTML representation of the content of the message.
    """

    content_type: Optional[Literal["html", "text"]] = None
    "Type of the content."

    content: Optional[str] = None
    "The content of the body."

    text_content: Optional[str] = None
    "The text content of the body after stripping HTML tags."
