"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class TokenPostResource(CustomBaseModel):
    """A post resource for a token."""

    sas_url: Optional[str] = None
    """
    The SAS URL.
    """
