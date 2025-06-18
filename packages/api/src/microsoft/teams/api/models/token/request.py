"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from ..custom_base_model import CustomBaseModel


class TokenRequest(CustomBaseModel):
    """A request to receive a user token."""

    provider: str
    """
    The provider to request a user token from.
    """
    settings: Dict[str, Any]
    """
    A collection of settings for the specific provider for this request.
    """
