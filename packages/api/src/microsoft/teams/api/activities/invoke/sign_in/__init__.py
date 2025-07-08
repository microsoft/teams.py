"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .token_exchange import SignInTokenExchangeInvokeActivity
from .verify_state import SignInVerifyStateInvokeActivity

SignInInvokeActivity = Annotated[
    Union[SignInTokenExchangeInvokeActivity, SignInVerifyStateInvokeActivity],
    Field(discriminator="name"),
]

__all__ = [
    "SignInTokenExchangeInvokeActivity",
    "SignInVerifyStateInvokeActivity",
    "SignInInvokeActivity",
]
