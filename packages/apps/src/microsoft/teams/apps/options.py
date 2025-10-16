"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Awaitable, Callable, List, Optional, TypedDict, Union, cast

from microsoft.teams.common import Storage
from typing_extensions import Unpack

from .plugins import PluginBase


class AppOptions(TypedDict, total=False):
    """Configuration options for the Teams App."""

    # Authentication credentials
    client_id: Optional[str]
    client_secret: Optional[str]
    tenant_id: Optional[str]
    # Custom token provider function
    token: Optional[Callable[[Union[str, list[str]], Optional[str]], Union[str, Awaitable[str]]]]

    # Infrastructure
    logger: Optional[Logger]
    storage: Optional[Storage[str, Any]]
    plugins: Optional[List[PluginBase]]
    skip_auth: Optional[bool]

    # Oauth
    default_connection_name: Optional[str]


@dataclass
class InternalAppOptions:
    """Internal dataclass for AppOptions with defaults and non-nullable fields."""

    # Fields with defaults
    skip_auth: bool = False
    default_connection_name: str = "graph"
    plugins: List[PluginBase] = field(default_factory=lambda: [])

    # Optional fields
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    token: Optional[Callable[[Union[str, list[str]], Optional[str]], Union[str, Awaitable[str]]]] = None
    logger: Optional[Logger] = None
    storage: Optional[Storage[str, Any]] = None

    @classmethod
    def from_typeddict(cls, options: AppOptions) -> "InternalAppOptions":
        """
        Create InternalAppOptions from AppOptions TypedDict with defaults applied.

        Args:
            options: AppOptions TypedDict (potentially with None values)

        Returns:
            InternalAppOptions with proper defaults and non-nullable required fields
        """
        kwargs: dict[str, Any] = {k: v for k, v in options.items() if v is not None}
        return cls(**kwargs)


def merge_app_options_with_defaults(**options: Unpack[AppOptions]) -> AppOptions:
    """
    Create AppOptions with default values merged with provided options.

    Args:
        **options: Configuration options to override defaults

    Returns:
        AppOptions with defaults applied
    """
    defaults: AppOptions = {
        "skip_auth": False,
        "default_connection_name": "graph",
        "plugins": [],
    }

    return cast(AppOptions, {**defaults, **options})
