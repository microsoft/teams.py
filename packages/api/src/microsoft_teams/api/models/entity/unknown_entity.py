"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from ..custom_base_model import CustomBaseModel


class UnknownEntity(CustomBaseModel):
    """Entity for unknown or forward-compatible types."""

    type: str
    "Type identifier for the unknown entity."
