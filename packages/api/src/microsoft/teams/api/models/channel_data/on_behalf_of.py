"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class OnBehalfOf(CustomBaseModel):
    """
    Represents information about a user on behalf of whom an action is performed.
    """

    item_id: int = 0
    "The ID of the item."

    mention_type: str
    "The type of mention."

    mri: str
    "The Microsoft Resource Identifier (MRI) of the user."

    display_name: Optional[str] = None
    "The display name of the user."
