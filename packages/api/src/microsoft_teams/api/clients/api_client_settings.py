"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
from dataclasses import dataclass
from typing import Optional

from ..auth.cloud_environment import PUBLIC, CloudEnvironment


@dataclass
class ApiClientSettings:
    """
    Settings for API clients.

    Attributes:
        oauth_url: The URL to use for managing user OAuth tokens.
                   Specify this value if you are using a regional bot.
                   For example: https://europe.token.botframework.com
                   Defaults to the cloud environment's token service URL.
    """

    oauth_url: Optional[str] = None


def merge_api_client_settings(
    api_client_settings: Optional[ApiClientSettings] = None,
    cloud: CloudEnvironment = PUBLIC,
) -> ApiClientSettings:
    """
    Merge API client settings with environment variables and defaults.

    Args:
        api_client_settings: Optional API client settings to merge.
        cloud: Cloud environment for default oauth_url. Defaults to PUBLIC.

    Returns:
        Merged API client settings.
    """
    env_oauth_url = os.environ.get("OAUTH_URL")

    if api_client_settings and api_client_settings.oauth_url:
        return api_client_settings

    return ApiClientSettings(oauth_url=env_oauth_url or cloud.token_service_url)
