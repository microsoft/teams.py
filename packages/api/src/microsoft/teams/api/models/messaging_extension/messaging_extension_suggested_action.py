from typing import List, Optional

from ..custom_base_model import CustomBaseModel


# Placeholder for external type
class CardAction(CustomBaseModel):
    """Placeholder for CardAction model from ../card"""

    pass


class MessagingExtensionSuggestedAction(CustomBaseModel):
    """
    Messaging extension Actions (Only when type is auth or config)
    """

    actions: Optional[List[CardAction]] = None
    "Actions"
