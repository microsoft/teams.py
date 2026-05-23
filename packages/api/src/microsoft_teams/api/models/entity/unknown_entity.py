"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class UnknownEntity(CustomBaseModel):
    """Entity for unknown or forward-compatible types."""

    model_config = ConfigDict(extra="allow")

    # Type identifier for the unknown entity.
    type: str
    "Type identifier for the unknown entity."
