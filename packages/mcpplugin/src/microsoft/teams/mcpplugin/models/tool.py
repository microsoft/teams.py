"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from pydantic import BaseModel


class McpToolDetails(BaseModel):
    """Details of an MCP tool."""

    name: str
    description: str
    input_schema: Dict[str, Any]
