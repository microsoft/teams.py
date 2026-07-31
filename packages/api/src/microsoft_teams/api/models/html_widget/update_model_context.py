"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel
from .call_tool_result import McpUiCallToolResultContent

McpUiContentBlock = McpUiCallToolResultContent
"""A content block in an MCP UI update-model-context request.
This reuses the same content union as McpUiCallToolResult,
as defined by the MCP Apps (ext-apps) specification."""


@experimental("ExperimentalTeamsHtmlWidget")
class McpUiUpdateModelContextParams(CustomBaseModel):
    """
    The parameters of an MCP UI ui/update-model-context request.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """

    content: Optional[list[McpUiContentBlock]] = None
    """An array of content blocks the widget wants to add to the model context."""

    structured_content: Optional[dict[str, Any]] = None
    """Structured data the widget wants to add to the model context."""


@experimental("ExperimentalTeamsHtmlWidget")
class McpUiUpdateModelContextRequest(CustomBaseModel):
    """
    A widget's request to update the model context, delivered on the
    value of a message activity (reusing the messageBack mechanism,
    fire-and-forget). Defined by the MCP Apps (ext-apps) specification.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """

    method: Literal["ui/update-model-context"] = "ui/update-model-context"
    """The MCP method discriminator."""

    params: McpUiUpdateModelContextParams
    """The request parameters."""
