"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import SignInStateVerifyQuery
from ...invoke_activity import InvokeActivity


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
