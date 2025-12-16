"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class TokenExchangeResource(CustomBaseModel):
    """Model representing a token exchange resource."""

    id: Optional[str] = None
    """
    The resource ID.
    """
    uri: Optional[str] = None
    """
    The resource URI.
    """
    provider_id: Optional[str] = None
    """
    The provider ID.
    """
