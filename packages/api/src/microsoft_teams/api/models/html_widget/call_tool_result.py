"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import Field

from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel


class McpUiTextContent(CustomBaseModel):
    """Text content item in an MCP call tool result."""

    type: Literal["text"] = "text"
    """Content type discriminator."""

    text: str
    """The text content."""


class McpUiImageContent(CustomBaseModel):
    """Image content item in an MCP call tool result."""

    type: Literal["image"] = "image"
    """Content type discriminator."""

    data: str
    """Base64-encoded image data."""

    mime_type: str
    """MIME type of the image (e.g. "image/png")."""


class McpUiAudioContent(CustomBaseModel):
    """Audio content item in an MCP call tool result."""

    type: Literal["audio"] = "audio"
    """Content type discriminator."""

    data: str
    """Base64-encoded audio data."""

    mime_type: str
    """MIME type of the audio (e.g. "audio/wav")."""


class McpUiResourceContent(CustomBaseModel):
    """Embedded resource content item in an MCP call tool result."""

    type: Literal["resource"] = "resource"
    """Content type discriminator."""

    resource: dict[str, Any]
    """The embedded resource (uri, mimeType, text or blob)."""


McpUiCallToolResultContent = Annotated[
    Union[McpUiTextContent, McpUiImageContent, McpUiAudioContent, McpUiResourceContent],
    Field(discriminator="type"),
]
"""A content item in an MCP UI call tool result.
Teams currently only renders text content; other types are defined
by the MCP spec for forward compatibility."""


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
