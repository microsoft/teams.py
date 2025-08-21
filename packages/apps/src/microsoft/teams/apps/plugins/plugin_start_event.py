"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import NamedTuple


class PluginStartEvent(NamedTuple):
    """Event emitted when the plugin is started."""

    port: int
    """The port given to the app.start() method"""
