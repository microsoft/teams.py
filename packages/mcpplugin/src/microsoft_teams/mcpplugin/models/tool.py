"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class McpToolDetails(BaseModel):
    """
    Details of an MCP tool.

    Represents a tool available from an MCP server, including its name,
    description, and input schema for parameter validation.
    """

    name: str = Field(..., description="Unique identifier for the tool")
    description: str = Field(..., description="Human-readable description of what the tool does")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema defining the tool's input parameters")
