"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TokenExchangeResource(BaseModel):
    """Model representing a token exchange resource."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    id: Optional[str] = Field(None, description="The resource ID")
    uri: Optional[str] = Field(None, description="The resource URI")
    provider_id: Optional[str] = Field(None, description="The provider ID")
