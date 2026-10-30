"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Optional, Union

from pydantic import Field

from ..custom_base_model import CustomBaseModel
from .application_identity_type import ApplicationIdentityType


class MessageApp(CustomBaseModel):
    """
    Represents an application entity.
    """

    application_identity_type: Optional[
        Annotated[Union[ApplicationIdentityType, str], Field(union_mode="left_to_right")]
    ] = None
    "The type of application."

    id: str
    "The id of the application."

    display_name: Optional[str] = None
    "The plaintext display name of the application."
