"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class GetBotSignInUrlParams(BaseModel):
    """Parameters for getting a bot sign-in URL."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    state: str
    """
    The state parameter.
    """
    code_challenge: Optional[str] = None
    """
    The code challenge.
    """
    emulator_url: Optional[str] = None
    """
    The emulator URL.
    """
    final_redirect: Optional[str] = None
    """
    The final redirect URL.
    """


class GetBotSignInResourceParams(BaseModel):
    """Parameters for getting a bot sign-in resource."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="allow",
    )

    state: str
    """
    The state parameter.
    """
    code_challenge: Optional[str] = None
    """
    The code challenge.
    """
    emulator_url: Optional[str] = None
    """
    The emulator URL.
    """
    final_redirect: Optional[str] = None
    """
    The final redirect URL.
    """
