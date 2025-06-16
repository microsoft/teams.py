from typing import Literal, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# Placeholder for external type
class SuggestedActions(BaseModel):
    """Placeholder for SuggestedActions model from ../suggested-actions"""

    pass


class ConfigAuth(BaseModel):
    """
    The bot's authentication config for SuggestedActions
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            serialization_alias=to_camel,
        ),
        extra="allow",
    )

    suggested_actions: Optional[SuggestedActions] = Field(None, description="SuggestedActions for the Bot Config Auth")
    type: Literal["auth"] = Field("auth", description="Type of the Bot Config Auth")
