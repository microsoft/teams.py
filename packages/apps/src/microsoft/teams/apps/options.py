"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, List, Optional

from microsoft.teams.common.storage import Storage

from .plugins import PluginBase


@dataclass
class AppOptions:
    """Configuration options for the Teams App."""

    # Authentication credentials
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None

    # Infrastructure
    logger: Optional[Logger] = None
    storage: Optional[Storage[str, Any]] = None
    plugins: List[PluginBase] = field(default_factory=list[PluginBase])
    enable_token_validation: bool = True

    # Oauth
    default_connection_name: str = "graph"
