"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import SignInStateVerifyQuery
from ...invoke_activity import InvokeActivity
from ...utils import input_model


class SignInVerifyStateInvokeActivity(InvokeActivity):
    """
    Sign-in verify state invoke activity for signin/verifyState invokes.

    Represents an invoke activity when state verification occurs
    during the sign-in process.
    """

    name: Literal["signin/verifyState"] = "signin/verifyState"  #
    """The name of the operation associated with an invoke or event activity."""

    value: SignInStateVerifyQuery
    """A value that is associated with the activity."""


@input_model
class SignInVerifyStateInvokeActivityInput(SignInVerifyStateInvokeActivity):
    """
    Input type for SignInVerifyStateInvokeActivity where ActivityBase fields are optional
    but invoke-specific fields retain their required status.
    """

    pass
