"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class GetBotSignInUrlParams(BaseModel):
    """Parameters for getting a bot sign-in URL."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(serialization_alias=to_camel),
        extra="allow",
    )

    state: str = Field(..., description="The state parameter")
    code_challenge: Optional[str] = Field(None, description="The code challenge")
    emulator_url: Optional[str] = Field(None, description="The emulator URL")
    final_redirect: Optional[str] = Field(None, description="The final redirect URL")


class GetBotSignInResourceParams(BaseModel):
    """Parameters for getting a bot sign-in resource."""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(serialization_alias=to_camel),
        extra="allow",
    )

    state: str = Field(..., description="The state parameter")
    code_challenge: Optional[str] = Field(None, description="The code challenge")
    emulator_url: Optional[str] = Field(None, description="The emulator URL")
    final_redirect: Optional[str] = Field(None, description="The final redirect URL")
