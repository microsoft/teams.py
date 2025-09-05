"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Any, List, Optional, TypedDict, cast

from microsoft.teams.common.storage import Storage
from typing_extensions import Unpack

from .plugins import PluginBase


class AppOptions(TypedDict, total=False):
    """Configuration options for the Teams App."""

    # Authentication credentials
    client_id: Optional[str]
    client_secret: Optional[str]
    tenant_id: Optional[str]

    # Infrastructure
    logger: Optional[Logger]
    storage: Optional[Storage[str, Any]]
    plugins: Optional[List[PluginBase]]
    enable_token_validation: Optional[bool]

    # Oauth
    default_connection_name: Optional[str]


def merge_app_options_with_defaults(**options: Unpack[AppOptions]) -> AppOptions:
    """
    Create AppOptions with default values merged with provided options.

    Args:
        **options: Configuration options to override defaults

    Returns:
        AppOptions with defaults applied
    """
    defaults: AppOptions = {
        "enable_token_validation": True,
        "default_connection_name": "graph",
        "plugins": [],
    }

    return cast(AppOptions, {**defaults, **options})
