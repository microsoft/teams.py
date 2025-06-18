"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from ..token import TokenPostResource
from ..token_exchange.resource import TokenExchangeResource


class SignInUrlResponse(BaseModel):
    """Response model for sign-in URL requests."""

    model_config = ConfigDict(
        alias_generator=to_camel,
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
