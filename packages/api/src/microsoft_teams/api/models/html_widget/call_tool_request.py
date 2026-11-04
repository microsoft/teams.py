"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel


@experimental("ExperimentalTeamsHtmlWidget")
class CallToolRequest(CustomBaseModel):
    """
    A request from a widget to call a tool on the bot.
    Sent as the value of an htmlwidget/calltool invoke activity.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """

    name: str
    """The name of the tool to call."""

    arguments: Optional[Any] = None
    """The arguments to pass to the tool.
    The Teams client adds arguments.__msteams__ = { mcpUrl, correlationId } to every callTool request,
    overwriting any value the bot supplied, and it is passed through untouched.
    Handlers should ignore it, validate arguments, never throw, and not authorize from activity.from."""
