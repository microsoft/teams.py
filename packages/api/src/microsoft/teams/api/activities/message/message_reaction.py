"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional, Self

from ...models import ActivityBase, ActivityInputBase, MessageReaction
from ...models.custom_base_model import CustomBaseModel


class _MessageReactionBase(CustomBaseModel):
    """Base class containing shared message reaction activity fields (all Optional except type)."""

    type: Literal["messageReaction"] = "messageReaction"

    reactions_added: Optional[List[MessageReaction]] = None
    """The collection of reactions added to the conversation."""

    reactions_removed: Optional[List[MessageReaction]] = None
    """The collection of reactions removed from the conversation."""


class MessageReactionActivity(_MessageReactionBase, ActivityBase):
    """Output model for received message reaction activities with required fields and read-only properties."""


class MessageReactionActivityInput(_MessageReactionBase, ActivityInputBase):
    """Input model for creating message reaction activities with builder methods."""

    def add_reaction(self, reaction: MessageReaction) -> Self:
        """
        Add a message reaction to the added reactions list.

        Args:
            reaction: The reaction to add

        Returns:
            Self for method chaining
        """
        if not self.reactions_added:
            self.reactions_added = []

        self.reactions_added.append(reaction)
        return self

    def remove_reaction(self, reaction: MessageReaction) -> Self:
        """
        Remove a message reaction and add it to the removed reactions list.

        This method will:
        1. Remove the reaction from reactions_added if it exists
        2. Add the reaction to reactions_removed

        Args:
            reaction: The reaction to remove

        Returns:
            Self for method chaining
        """
        # Remove from added reactions if it exists
        if self.reactions_added:
            # Find and remove matching reaction
            for i, added_reaction in enumerate(self.reactions_added):
                added_user = getattr(added_reaction, "user", None)
                reaction_user = getattr(reaction, "user", None)
                added_user_id = added_user.id if added_user else None
                reaction_user_id = reaction_user.id if reaction_user else None

                if added_reaction.type == reaction.type and added_user_id == reaction_user_id:
                    self.reactions_added.pop(i)
                    break

        # Add to removed reactions
        if not self.reactions_removed:
            self.reactions_removed = []

        self.reactions_removed.append(reaction)
        return self
