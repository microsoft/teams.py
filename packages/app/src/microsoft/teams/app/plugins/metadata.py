"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Literal, Optional, Type, Union

from ..plugins.plugin_base import PluginBase

PLUGIN_METADATA_KEY = "teams:plugin"


@dataclass
class PluginOptions:
    """Plugin metadata"""

    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None


def Plugin(name: Optional[str] = None, version: Optional[str] = None, description: Optional[str] = None) -> Any:
    """Turns any class into a plugin using the decorator pattern."""

    def decorator(cls: Type[Any]) -> Any:
        plugin_name = name or cls.__name__
        plugin_version = version or "0.0.0"
        plugin_description = description or ""
        updated_metadata = PluginOptions(name=plugin_name, version=plugin_version, description=plugin_description)
        setattr(cls, PLUGIN_METADATA_KEY, updated_metadata)
        return cls

    return decorator


def get_metadata(cls: Type[PluginBase]) -> PluginOptions:
    """Get plugin metadata from a class."""
    metadata = getattr(cls, PLUGIN_METADATA_KEY, None)
    if not metadata:
        raise ValueError(f"type {cls.__name__} is not a valid plugin")
    return metadata


PluginEventName = Literal["error", "activity", "custom"]


@dataclass
class EventMetadata:
    """Information associated with the plugin event"""

    name: PluginEventName
    "The name of the event."


@dataclass
class DependencyMetadata:
    """Information associated with a plugin dependency"""

    name: Optional[str] = None
    "The name used to resolve the dependency."

    optional: Optional[bool] = False
    "If optional, the app will not throw if the dependency is not found."


@dataclass
class IdDependencyOptions(DependencyMetadata):
    name = "id"
    optional = True


@dataclass
class NameDependencyOptions(DependencyMetadata):
    name = "name"
    optional = True


@dataclass
class ManifestDependencyOptions:
    name = "manifest"
    optional: Optional[bool] = False


@dataclass
class CredentialsDependencyOptions(DependencyMetadata):
    name = "credentials"
    optional = True


@dataclass
class BotTokenDependencyOptions(DependencyMetadata):
    name = "bot_token"
    optional = True


@dataclass
class GraphTokenDependencyOptions(DependencyMetadata):
    name = "graph_token"
    optional = True


@dataclass
class LoggerDependencyOptions(DependencyMetadata):
    name = "logger"
    optional = False


@dataclass
class StorageDependencyOptions(DependencyMetadata):
    name = "storage"
    optional: Optional[bool] = False


@dataclass
class PluginDependencyOptions(DependencyMetadata):
    name: Optional[str] = None
    optional: Optional[bool] = None


DependencyOptions = Union[
    IdDependencyOptions,
    NameDependencyOptions,
    ManifestDependencyOptions,
    CredentialsDependencyOptions,
    BotTokenDependencyOptions,
    GraphTokenDependencyOptions,
    LoggerDependencyOptions,
    StorageDependencyOptions,
    PluginDependencyOptions,
]
