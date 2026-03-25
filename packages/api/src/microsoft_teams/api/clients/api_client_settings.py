"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..auth.cloud_environment import CloudEnvironment


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


def merge_api_client_settings(
    api_client_settings: Optional[ApiClientSettings] = None,
    cloud: Optional["CloudEnvironment"] = None,
) -> ApiClientSettings:
    """
    Merge API client settings with environment variables and defaults.

    Args:
        api_client_settings: Optional API client settings to merge.
        cloud: Optional cloud environment for default oauth_url.

    Returns:
        Merged API client settings.
    """
    if api_client_settings is None:
        api_client_settings = ApiClientSettings()

    # Check for environment variable override
    env_oauth_url = os.environ.get("OAUTH_URL")
    default_oauth_url = cloud.token_service_url if cloud else DEFAULT_API_CLIENT_SETTINGS.oauth_url

    return ApiClientSettings(
        oauth_url=api_client_settings.oauth_url
        if api_client_settings.oauth_url != DEFAULT_API_CLIENT_SETTINGS.oauth_url
        else (env_oauth_url or default_oauth_url)
    )
