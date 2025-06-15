"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, Optional, Union

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ClientCredentials(BaseModel):
    """Credentials for authentication of an app via clientId and clientSecret."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    client_id: str = Field(..., description="The client ID")
    client_secret: str = Field(..., description="The client secret")
    tenant_id: Optional[str] = Field(None, description="The tenant ID")


class TokenCredentials(BaseModel):
    """Credentials for authentication of an app via any external auth method."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    client_id: str = Field(..., description="The client ID")
    tenant_id: Optional[str] = Field(None, description="The tenant ID")
    # (scope: string | string[], tenantId?: string) => string | Promise<string>
    token: Callable[[Union[str, list[str]], Optional[str]], Union[str, Awaitable[str]]] = Field(
        ..., description="The token function"
    )


# Union type for credentials
Credentials = Union[ClientCredentials, TokenCredentials]
