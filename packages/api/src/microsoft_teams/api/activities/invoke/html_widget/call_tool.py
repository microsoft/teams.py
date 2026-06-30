"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from microsoft_teams.common.experimental import experimental

from ....models.html_widget.call_tool_request import CallToolRequest
from ...invoke_activity import InvokeActivity


@experimental("ExperimentalTeamsHtmlWidget")
class HtmlWidgetCallToolInvokeActivity(InvokeActivity):
    """
    Represents an activity that is sent when a widget calls a tool on the bot.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """

    type: Literal["invoke"] = "invoke"

    name: Literal["htmlwidget/calltool"] = "htmlwidget/calltool"
    """The name of the operation associated with the invoke activity."""

    value: CallToolRequest
    """The tool call request from the widget."""
