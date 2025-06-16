from typing import List

from pydantic import BaseModel, Field


# Placeholder for external type
class Account(BaseModel):
    """Placeholder for Account model from ../account"""

    pass


class Conversation(BaseModel):
    """
    Conversation and its members
    """

    id: str = Field(..., description="Conversation ID")
    members: List[Account] = Field(..., description="List of members in this conversation")
