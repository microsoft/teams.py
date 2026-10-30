"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Optional, Union

from pydantic import Field

from ..custom_base_model import CustomBaseModel
from .user_identity_type import UserIdentityType


class MessageUser(CustomBaseModel):
    """
    Represents a user entity.
    """

    user_identity_type: Optional[Annotated[Union[UserIdentityType, str], Field(union_mode="left_to_right")]] = None
    "The identity type of the user."

    id: str
    "The id of the user."

    display_name: Optional[str] = None
    "The plaintext display name of the user."
