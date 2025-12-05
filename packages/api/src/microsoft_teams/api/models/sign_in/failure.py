"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class SignInFailure(CustomBaseModel):
    """
    Sign-in failure information.

    Represents the details of a sign-in failure including
    an error code and message.
    """

    code: Optional[str] = None
    """
    The error code for the sign-in failure
    """
    message: Optional[str] = None
    """
    The error message for the sign-in failure
    """
