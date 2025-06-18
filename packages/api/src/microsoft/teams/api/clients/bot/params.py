"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ...models.custom_base_model import CustomBaseModel


class GetBotSignInUrlParams(CustomBaseModel):
    """Parameters for getting a bot sign-in URL."""

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


class GetBotSignInResourceParams(CustomBaseModel):
    """Parameters for getting a bot sign-in resource."""

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
