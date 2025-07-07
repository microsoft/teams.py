"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .token_exchange import SignInTokenExchangeInvokeActivity
from .verify_state import SignInVerifyStateInvokeActivity

SignInInvokeActivity = Union[SignInTokenExchangeInvokeActivity, SignInVerifyStateInvokeActivity]

__all__ = [
    "SignInTokenExchangeInvokeActivity",
    "SignInVerifyStateInvokeActivity",
    "SignInInvokeActivity",
]
