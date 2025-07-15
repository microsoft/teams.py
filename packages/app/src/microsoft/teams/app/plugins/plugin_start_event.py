"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.api.models import CustomBaseModel


class PluginStartEvent(CustomBaseModel):
    """Event emitted when the plugin is started."""

    port: int
    """The port given to the app.start() method"""
