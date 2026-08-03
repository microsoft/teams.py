"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Keep the deprecated BotClient re-export for backwards compatibility until it is removed.
from .client import BotClient  # pyright: ignore[reportDeprecated]
from .params import GetBotSignInResourceParams, GetBotSignInUrlParams
from .sign_in_client import BotSignInClient
from .token_client import BotTokenClient

__all__ = [
    "BotClient",
    "BotSignInClient",
    "BotTokenClient",
    "GetBotSignInResourceParams",
    "GetBotSignInUrlParams",
]
