from typing import Literal, Union

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


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

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    status_code: Literal[200] = Field(200)
    type: Literal["application/vnd.microsoft.card.adaptive"]
    value: IAdaptiveCard


class AdaptiveCardActionMessageResponse(BaseModel):
    """
    The request was successfully processed, and the response includes a message
    that the client should display
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    status_code: Literal[200] = Field(200)
    type: Literal["application/vnd.microsoft.activity.message"]
    value: str


class AdaptiveCardActionErrorResponse(BaseModel):
    """
    `400`: The incoming request was invalid
    `500`: An unexpected error occurred
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    status_code: Literal[400, 500] = Field(...)
    type: Literal["application/vnd.microsoft.error"]
    value: HttpError


class AdaptiveCardActionLoginResponse(BaseModel):
    """The client needs to prompt the user to authenticate"""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    status_code: Literal[401] = Field(401)
    type: Literal["application/vnd.microsoft.activity.loginRequest"]
    value: OAuthCard


class AdaptiveCardActionIncorrectAuthCodeResponse(BaseModel):
    """
    The authentication state passed by the client was incorrect and
    authentication failed
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    status_code: Literal[401] = Field(401)
    type: Literal["application/vnd.microsoft.error.incorrectAuthCode"]
    value: None


class AdaptiveCardActionPreconditionFailedResponse(BaseModel):
    """The SSO authentication flow failed"""

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    status_code: Literal[412] = Field(412)
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
