"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Awaitable, Callable, List, Mapping, Optional, Union

from .tool import McpToolDetails


@dataclass
class McpClientPluginParams:
    """
    Parameters for MCP client plugin configuration.

    Configures how the MCP client plugin connects to and interacts with
    MCP servers, including transport options, caching behavior, and error handling.
    """

    transport: Optional[str] = "streamable_http"  # Transport protocol for MCP connection
    available_tools: Optional[List[McpToolDetails]] = None  # Pre-defined tools (skips server fetch)
    headers: Optional[Mapping[str, Union[str, Callable[[], Union[str, Awaitable[str]]]]]] = (
        None  # HTTP headers for requests
    )
    skip_if_unavailable: Optional[bool] = True  # Continue if server is unavailable
    refetch_timeout_ms: Optional[int] = None  # Override default cache timeout
