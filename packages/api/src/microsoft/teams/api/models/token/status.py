"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TokenStatus(BaseModel):
    """The status of a particular token."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    channel_id: str = Field(..., description="The channel ID")
    connection_name: str = Field(..., description="The connection name")
    has_token: bool = Field(..., description="Boolean indicating if a token is stored for this ConnectionName")
    service_provider_display_name: str = Field(
        ..., description="The display name of the service provider for which this Token belongs to"
    )
