"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import SignInExchangeToken
from ...invoke_activity import InvokeActivity
from ...utils import input_model


class SignInTokenExchangeInvokeActivity(InvokeActivity):
    """
    Sign-in token exchange invoke activity for signin/tokenExchange invokes.

    Represents an invoke activity when a token exchange occurs
    during the sign-in process.
    """

    name: Literal["signin/tokenExchange"] = "signin/tokenExchange"  # pyright: ignore [reportIncompatibleVariableOverride]
    """The name of the operation associated with an invoke or event activity."""

    value: SignInExchangeToken
    """A value that is associated with the activity."""


@input_model
class SignInTokenExchangeInvokeActivityInput(SignInTokenExchangeInvokeActivity):
    """
    Input type for SignInTokenExchangeInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
