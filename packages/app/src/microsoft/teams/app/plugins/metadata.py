"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Literal, Optional, Union

PLUGIN_METADATA_KEY = "teams:plugin"


@dataclass
class PluginOptions:
    """Plugin metadata"""

    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None


def plugin(metadata: Optional[PluginOptions] = None):
    """Turns any class into a plugin using the decorator pattern."""

    def decorator(cls: Any) -> Any:
        if metadata is None:
            updated_metadata = PluginOptions(name=cls.__name__, version="0.0.0", description="")
            setattr(cls, PLUGIN_METADATA_KEY, updated_metadata)
        else:
            name = metadata.name or cls.__name__
            version = metadata.version or "0.0.0"
            description = metadata.description or ""
            updated_metadata = PluginOptions(name=name, version=version, description=description)
            setattr(cls, PLUGIN_METADATA_KEY, updated_metadata)
        return cls

    return decorator


def get_metadata(cls: Any) -> Optional[PluginOptions]:
    """Get plugin metadata from a class."""
    return getattr(cls, PLUGIN_METADATA_KEY, None)


PluginEventName = Literal["error", "activity", "custom"]


@dataclass
class EventMetadata:
    """Information associated with the plugin event"""

    name: PluginEventName
    "The name of the event."


@dataclass
class DependencyMetadata:
    """Metadata for a plugin dependency"""

    name: Optional[str] = None
    optional: Optional[bool] = False


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
