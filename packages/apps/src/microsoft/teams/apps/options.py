"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, List, Optional, TypedDict

from microsoft.teams.common.storage import Storage

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
    plugins: List[PluginBase]
    enable_token_validation: bool

    # Oauth
    default_connection_name: str


@dataclass
class AppOptionsDefaults:
    """Default values for AppOptions."""

    enable_token_validation: bool = True
    default_connection_name: str = "graph"
    plugins: List[PluginBase] = field(default_factory=list[PluginBase])
