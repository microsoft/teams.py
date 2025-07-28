"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from ..card.card_action import CardAction
from ..custom_base_model import CustomBaseModel
from ..token import TokenPostResource
from ..token_exchange import TokenExchangeResource


class OAuthCard(CustomBaseModel):
    "A card representing a request to perform a sign in via OAuth"

    text: str
    "Text for signin request"

    connection_name: str
    "The name of the registered connection"

    token_exchange_resource: Optional[TokenExchangeResource] = None
    "The token exchange resource for single sign on"

    token_post_resource: Optional[TokenPostResource] = None
    "The token for directly post a token to token service"

    buttons: Optional[List[CardAction]] = None
