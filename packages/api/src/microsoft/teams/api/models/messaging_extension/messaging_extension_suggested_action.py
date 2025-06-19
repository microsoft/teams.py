"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from ..card import CardAction
from ..custom_base_model import CustomBaseModel


class MessagingExtensionSuggestedAction(CustomBaseModel):
    """
    Messaging extension Actions (Only when type is auth or config)
    """

    actions: Optional[List[CardAction]] = None
    "Actions"
