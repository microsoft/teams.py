"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ApiClientSettings:
    """
    Settings for API clients.

    Attributes:
        oauth_url: The URL to use for managing user OAuth tokens.
                   Specify this value if you are using a regional bot.
                   For example: https://europe.token.botframework.com
                   Default is https://token.botframework.com
    """

    oauth_url: str = "https://token.botframework.com"


DEFAULT_API_CLIENT_SETTINGS = ApiClientSettings()


def merge_api_client_settings(api_client_settings: Optional[ApiClientSettings]) -> ApiClientSettings:
    """
    Merge API client settings with environment variables and defaults.

    Args:
        api_client_settings: Optional API client settings to merge.

    Returns:
        Merged API client settings.
    """
    if api_client_settings is None:
        api_client_settings = ApiClientSettings()

    # Check for environment variable override
    env_oauth_url = os.environ.get("OAUTH_URL")

    return ApiClientSettings(oauth_url=env_oauth_url if env_oauth_url else api_client_settings.oauth_url)
