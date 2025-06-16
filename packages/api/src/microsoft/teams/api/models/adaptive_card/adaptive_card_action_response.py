from typing import Literal, Union

from pydantic import BaseModel, Field


# Placeholder for external types
class IAdaptiveCard(BaseModel):
    """Placeholder for @microsoft/teams.cards IAdaptiveCard"""

    pass


class HttpError(BaseModel):
    """Placeholder for error model"""

    pass


class OAuthCard(BaseModel):
    """Placeholder for oauth model"""

    pass


class AdaptiveCardActionCardResponse(BaseModel):
    """
    The request was successfully processed, and the response includes
    an Adaptive Card that the client should display in place of the current one
    """

    status_code: Literal[200] = Field(200, alias="statusCode")
    type: Literal["application/vnd.microsoft.card.adaptive"]
    value: IAdaptiveCard


class AdaptiveCardActionMessageResponse(BaseModel):
    """
    The request was successfully processed, and the response includes a message
    that the client should display
    """

    status_code: Literal[200] = Field(200, alias="statusCode")
    type: Literal["application/vnd.microsoft.activity.message"]
    value: str


class AdaptiveCardActionErrorResponse(BaseModel):
    """
    `400`: The incoming request was invalid
    `500`: An unexpected error occurred
    """

    status_code: Literal[400, 500] = Field(..., alias="statusCode")
    type: Literal["application/vnd.microsoft.error"]
    value: HttpError


class AdaptiveCardActionLoginResponse(BaseModel):
    """The client needs to prompt the user to authenticate"""

    status_code: Literal[401] = Field(401, alias="statusCode")
    type: Literal["application/vnd.microsoft.activity.loginRequest"]
    value: OAuthCard


class AdaptiveCardActionIncorrectAuthCodeResponse(BaseModel):
    """
    The authentication state passed by the client was incorrect and
    authentication failed
    """

    status_code: Literal[401] = Field(401, alias="statusCode")
    type: Literal["application/vnd.microsoft.error.incorrectAuthCode"]
    value: None


class AdaptiveCardActionPreconditionFailedResponse(BaseModel):
    """The SSO authentication flow failed"""

    status_code: Literal[412] = Field(412, alias="statusCode")
    type: Literal["application/vnd.microsoft.error.preconditionFailed"]
    value: HttpError


AdaptiveCardActionResponse = Union[
    AdaptiveCardActionCardResponse,
    AdaptiveCardActionMessageResponse,
    AdaptiveCardActionErrorResponse,
    AdaptiveCardActionLoginResponse,
    AdaptiveCardActionIncorrectAuthCodeResponse,
    AdaptiveCardActionPreconditionFailedResponse,
]
