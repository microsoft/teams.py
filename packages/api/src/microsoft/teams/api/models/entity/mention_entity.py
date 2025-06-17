from typing import Literal, Optional

from pydantic import ConfigDict

from ..custom_base_model import CustomBaseModel


# Placeholder for Account type
class Account(CustomBaseModel):
    """Placeholder for Account model from ../account"""

    pass


class MentionEntity(CustomBaseModel):
    """Entity representing a mention of a user"""

    model_config = ConfigDict(
        **CustomBaseModel.model_config,
        extra="allow",
    )

    type: Literal["mention"] = "mention"
    "Type identifier for mention"

    mentioned: Account
    "The mentioned user"

    text: Optional[str] = None
    "Text which represents the mention"
