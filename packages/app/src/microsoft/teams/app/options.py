"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Callable, List, Optional

from microsoft.teams.common.storage import Storage

from .plugin import PluginProtocol


@dataclass
class AppOptions:
    """Configuration options for the Teams App."""

    # Authentication credentials
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None

    # Activity handling
    # TODO: Update when routing is implemented
    activity_handler: Optional[Callable[..., Any]] = None

    # Infrastructure
    logger: Optional[Logger] = None
    storage: Optional[Storage[str, Any]] = None
    plugins: List[PluginProtocol] = field(default_factory=list[PluginProtocol])
