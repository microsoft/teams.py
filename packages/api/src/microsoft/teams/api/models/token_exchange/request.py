"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class TokenExchangeRequest(CustomBaseModel):
    """Model representing a token exchange request."""

    uri: Optional[str] = None
    """
    The request URI.
    """
    token: Optional[str] = None
    """
    The token to exchange.
    """
