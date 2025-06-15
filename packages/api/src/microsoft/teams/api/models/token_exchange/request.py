"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TokenExchangeRequest(BaseModel):
    """Model representing a token exchange request."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    uri: Optional[str] = Field(None, description="The request URI")
    token: Optional[str] = Field(None, description="The token to exchange")
