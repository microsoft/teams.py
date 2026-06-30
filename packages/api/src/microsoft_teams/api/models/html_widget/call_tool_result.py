"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel


class McpUiCallToolResultContent(CustomBaseModel):
    """A content item in an MCP UI call tool result."""

    type: str
    """The type of content (e.g. "text")."""

    text: str
    """The text content."""


@experimental("ExperimentalTeamsHtmlWidget")
class McpUiCallToolResult(CustomBaseModel):
    """
    The result of a widget's tools/call request, returned by the bot
    in response to an htmlwidget/calltool invoke activity.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """

    content: Optional[list[McpUiCallToolResultContent]] = None
    """An array of content items to return to the widget."""

    structured_content: Optional[Any] = None
    """Structured data that the widget can render from."""

    is_error: Optional[bool] = None
    """Whether the tool call resulted in an error."""


@experimental("ExperimentalTeamsHtmlWidget")
class HtmlWidgetCallToolResponse(CustomBaseModel):
    """
    The wire-format response body for an htmlwidget/calltool invoke.
    Teams expects this shape (with responseType discriminator) rather than
    a bare McpUiCallToolResult.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """

    response_type: Literal["htmlwidget/calltoolresult"] = "htmlwidget/calltoolresult"
    """Discriminator that tells Teams how to interpret the response."""

    call_tool_result: McpUiCallToolResult
    """The tool call result payload."""
