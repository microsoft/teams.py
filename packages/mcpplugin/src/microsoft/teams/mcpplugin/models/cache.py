"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from .tool import McpToolDetails


class McpCachedValue:
    """Cached value for MCP server data."""

    def __init__(
        self,
        transport: Optional[str] = None,
        available_tools: Optional[List[McpToolDetails]] = None,
        last_fetched: Optional[float] = None,
    ):
        self.transport = transport
        self.available_tools = available_tools or []
        self.last_fetched = last_fetched
