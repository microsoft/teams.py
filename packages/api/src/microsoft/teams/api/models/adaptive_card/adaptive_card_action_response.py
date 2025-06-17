"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Union

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


# Placeholder for external types
class IAdaptiveCard(CustomBaseModel):
    """Placeholder for @microsoft/teams.cards IAdaptiveCard"""

    pass


class HttpError(CustomBaseModel):
    """Placeholder for error model"""

    pass


class OAuthCard(CustomBaseModel):
    """Placeholder for oauth model"""

    pass


class AdaptiveCardActionCardResponse(CustomBaseModel):
    """
    The request was successfully processed, and the response includes
    an Adaptive Card that the client should display in place of the current one
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    status_code: Literal[200] = 200
    type: Literal["application/vnd.microsoft.card.adaptive"] = "application/vnd.microsoft.card.adaptive"
    value: IAdaptiveCard


class AdaptiveCardActionMessageResponse(CustomBaseModel):
    """
    The request was successfully processed, and the response includes a message
    that the client should display
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    status_code: Literal[200] = 200
    type: Literal["application/vnd.microsoft.activity.message"] = "application/vnd.microsoft.activity.message"
    value: str


class AdaptiveCardActionErrorResponse(CustomBaseModel):
    """
    `400`: The incoming request was invalid
    `500`: An unexpected error occurred
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    status_code: Literal[400, 500]
    type: Literal["application/vnd.microsoft.error"] = "application/vnd.microsoft.error"
    value: HttpError


class AdaptiveCardActionLoginResponse(CustomBaseModel):
    """The client needs to prompt the user to authenticate"""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    status_code: Literal[401] = 401
    type: Literal["application/vnd.microsoft.activity.loginRequest"] = "application/vnd.microsoft.activity.loginRequest"
    value: OAuthCard


class AdaptiveCardActionIncorrectAuthCodeResponse(CustomBaseModel):
    """
    The authentication state passed by the client was incorrect and
    authentication failed
    """

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    status_code: Literal[401] = 401
    type: Literal["application/vnd.microsoft.error.incorrectAuthCode"] = (
        "application/vnd.microsoft.error.incorrectAuthCode"
    )
    value: None


class AdaptiveCardActionPreconditionFailedResponse(CustomBaseModel):
    """The SSO authentication flow failed"""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

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
