"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel


class SignInStateVerifyQuery(CustomBaseModel):
    """
    An interface representing SigninStateVerificationQuery.
    Signin state (part of signin action auth flow) verification invoke query
    """

    state: Optional[str] = None
    """
    The state string originally received when the
    signin web flow is finished with a state posted back to client via tab SDK
    microsoftTeams.authentication.notifySuccess(state)
    """
