"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Any, List, TypedDict, cast

from microsoft.teams.common.storage import Storage
from typing_extensions import NotRequired, Unpack

from .plugins import PluginBase


class AppOptions(TypedDict):
    """Configuration options for the Teams App."""

    # Authentication credentials
    client_id: NotRequired[str]
    client_secret: NotRequired[str]
    tenant_id: NotRequired[str]

    # Infrastructure
    logger: NotRequired[Logger]
    storage: NotRequired[Storage[str, Any]]
    plugins: NotRequired[List[PluginBase]]
    enable_token_validation: NotRequired[bool]

    # Oauth
    default_connection_name: NotRequired[str]


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
