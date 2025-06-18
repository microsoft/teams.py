"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel
from ..token import TokenPostResource
from ..token_exchange.resource import TokenExchangeResource


class SignInUrlResponse(CustomBaseModel):
    """Response model for sign-in URL requests."""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    sign_in_link: Optional[str] = None
    """
    The sign in link.
    """
    token_exchange_resource: Optional[TokenExchangeResource] = None
    """
    The token exchange resource.
    """
    token_post_resource: Optional[TokenPostResource] = None
    """
    The token post resource.
    """
