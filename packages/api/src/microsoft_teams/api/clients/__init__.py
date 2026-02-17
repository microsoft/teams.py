"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from . import bot, conversation, meeting, reaction, team, user
from .api_client import ApiClient
from .api_client_settings import DEFAULT_API_CLIENT_SETTINGS, ApiClientSettings, merge_api_client_settings
from .bot import *  # noqa: F403
from .conversation import *  # noqa: F403
from .meeting import *  # noqa: F403
from .reaction import *  # noqa: F403
from .team import *  # noqa: F403
from .user import *  # noqa: F403

# Combine all exports from submodules
__all__: list[str] = [
    "ApiClient",
    "ApiClientSettings",
    "DEFAULT_API_CLIENT_SETTINGS",
    "merge_api_client_settings",
]
__all__.extend(bot.__all__)
__all__.extend(conversation.__all__)
__all__.extend(meeting.__all__)
__all__.extend(reaction.__all__)
__all__.extend(team.__all__)
__all__.extend(user.__all__)
