"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ....models import SignInFailure
from ...invoke_activity import InvokeActivity


class SignInFailureInvokeActivity(InvokeActivity):
    """
    Sign-in failure invoke activity for signin/failure invokes.

    Represents an invoke activity when a sign-in operation fails
    during the authentication process.
    """

    name: Literal["signin/failure"] = "signin/failure"
    """The name of the operation associated with an invoke or event activity."""

    value: SignInFailure
    """A value that is associated with the activity."""
