"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .tool import McpToolDetails


@dataclass
class McpCachedValue:
    """
    Cached value for MCP server data.

    Stores fetched tool information from MCP servers along with metadata
    for cache management and expiration handling.
    """

    transport: Optional[str] = None  # Transport protocol used for this server
    available_tools: List[McpToolDetails] = field(default_factory=list[McpToolDetails])  # Cached tools from server
    last_fetched: Optional[float] = None  # Timestamp when tools were last fetched (milliseconds)
