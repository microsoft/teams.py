"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, List, Mapping, Optional, Union

from .tool import McpToolDetails


class McpClientPluginParams:
    """Parameters for MCP client plugin configuration."""

    def __init__(
        self,
        transport: Optional[str] = "streamable_http",
        available_tools: Optional[List[McpToolDetails]] = None,
        headers: Optional[Mapping[str, Union[str, Callable[[], Union[str, Awaitable[str]]]]]] = None,
        skip_if_unavailable: Optional[bool] = True,
        refetch_timeout_ms: Optional[int] = None,
    ):
        self.transport = transport
        self.available_tools = available_tools
        self.headers = headers
        self.skip_if_unavailable = skip_if_unavailable
        self.refetch_timeout_ms = refetch_timeout_ms
