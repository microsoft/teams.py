"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..account import Account
from ..custom_base_model import CustomBaseModel


class MentionEntity(CustomBaseModel):
    """Entity representing a mention of a user"""

    type: Literal["mention"] = "mention"
    "Type identifier for mention"

    mentioned: Account
    "The mentioned user"

    text: Optional[str] = None
    "Text which represents the mention"
