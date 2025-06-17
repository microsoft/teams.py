from typing import List

from ..custom_base_model import CustomBaseModel


# Placeholder for external type
class Account(CustomBaseModel):
    """Placeholder for Account model from ../account"""

    pass


class Conversation(CustomBaseModel):
    """
    Conversation and its members
    """

    id: str
    "Conversation ID"

    members: List[Account]
    "List of members in this conversation"
