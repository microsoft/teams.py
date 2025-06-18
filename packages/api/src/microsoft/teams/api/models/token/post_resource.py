"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


class TokenPostResource(CustomBaseModel):
    """A post resource for a token."""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    sas_url: Optional[str] = None
    """
    The SAS URL.
    """
