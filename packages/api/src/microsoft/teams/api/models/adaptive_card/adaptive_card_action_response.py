"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

from microsoft.teams.cards import AdaptiveCard

from ..custom_base_model import CustomBaseModel
from ..error import HttpError
from ..oauth import OAuthCard


class AdaptiveCardActionCardResponse(CustomBaseModel):
    """
    The request was successfully processed, and the response includes
    an Adaptive Card that the client should display in place of the current one
    """

    status_code: Literal[200] = 200
    type: Literal["application/vnd.microsoft.card.adaptive"] = "application/vnd.microsoft.card.adaptive"
    value: AdaptiveCard


class AdaptiveCardActionMessageResponse(CustomBaseModel):
    """
    The request was successfully processed, and the response includes a message
    that the client should display
    """

    status_code: Literal[200] = 200
    type: Literal["application/vnd.microsoft.activity.message"] = "application/vnd.microsoft.activity.message"
    value: str


class AdaptiveCardActionErrorResponse(CustomBaseModel):
    """
    `400`: The incoming request was invalid
    `500`: An unexpected error occurred
    """

    status_code: Literal[400, 500]
    type: Literal["application/vnd.microsoft.error"] = "application/vnd.microsoft.error"
    value: HttpError


class AdaptiveCardActionLoginResponse(CustomBaseModel):
    """The client needs to prompt the user to authenticate"""

    status_code: Literal[401] = 401
    type: Literal["application/vnd.microsoft.activity.loginRequest"] = "application/vnd.microsoft.activity.loginRequest"
    value: OAuthCard


class AdaptiveCardActionIncorrectAuthCodeResponse(CustomBaseModel):
    """
    The authentication state passed by the client was incorrect and
    authentication failed
    """

    status_code: Literal[401] = 401
    type: Literal["application/vnd.microsoft.error.incorrectAuthCode"] = (
        "application/vnd.microsoft.error.incorrectAuthCode"
    )
    value: None


class AdaptiveCardActionPreconditionFailedResponse(CustomBaseModel):
    """The SSO authentication flow failed"""

    status_code: Literal[412] = 412
    type: Literal["application/vnd.microsoft.error.preconditionFailed"] = (
        "application/vnd.microsoft.error.preconditionFailed"
    )
    value: HttpError


AdaptiveCardActionResponse = Union[
    AdaptiveCardActionCardResponse,
    AdaptiveCardActionMessageResponse,
    AdaptiveCardActionErrorResponse,
    AdaptiveCardActionLoginResponse,
    AdaptiveCardActionIncorrectAuthCodeResponse,
    AdaptiveCardActionPreconditionFailedResponse,
]
