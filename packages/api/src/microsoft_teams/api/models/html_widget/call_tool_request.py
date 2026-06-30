"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ...models.custom_base_model import CustomBaseModel


class CallToolRequest(CustomBaseModel):
    """
    A request from a widget to call a tool on the bot.
    Sent as the value of an htmlwidget/calltool invoke activity.
    """

    name: str
    """The name of the tool to call."""

    arguments: Optional[Any] = None
    """The arguments to pass to the tool."""
