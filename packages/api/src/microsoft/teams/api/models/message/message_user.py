"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .user_identity_type import UserIdentityType


class MessageUser(CustomBaseModel):
    """
    Represents a user entity.
    """

    user_identity_type: Optional[UserIdentityType] = None
    "The identity type of the user."

    id: str
    "The id of the user."

    display_name: Optional[str] = None
    "The plaintext display name of the user."
