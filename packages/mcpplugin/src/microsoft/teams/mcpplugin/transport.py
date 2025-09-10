"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, Dict, Mapping, Optional, Union

from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

ValueOrFactory = Union[str, Callable[[], Union[str, Awaitable[str]]]]


@asynccontextmanager
async def create_streamable_http_transport(
    url: str,
    headers: Optional[Mapping[str, ValueOrFactory]] = None,
):
    """Create a streamable HTTP transport for MCP communication."""
    resolved_headers: Dict[str, str] = {}
    if headers:
        for key, value in headers.items():
            if callable(value):
                resolved_value = value()
                if asyncio.iscoroutine(resolved_value):
                    resolved_value = await resolved_value
                resolved_headers[key] = str(resolved_value)
            else:
                resolved_headers[key] = str(value)

    async with streamablehttp_client(url, headers=resolved_headers) as (read_stream, write_stream, _):
        yield read_stream, write_stream


@asynccontextmanager
async def create_sse_transport(
    url: str,
    headers: Optional[Mapping[str, ValueOrFactory]] = None,
):
    """Create an SSE transport for MCP communication."""
    resolved_headers: Dict[str, str] = {}
    if headers:
        for key, value in headers.items():
            if callable(value):
                resolved_value = value()
                if asyncio.iscoroutine(resolved_value):
                    resolved_value = await resolved_value
                resolved_headers[key] = str(resolved_value)
            else:
                resolved_headers[key] = str(value)

    async with sse_client(url, headers=resolved_headers) as (read_stream, write_stream):
        yield read_stream, write_stream


def create_transport(
    url: str,
    transport_type: str = "streamable_http",
    headers: Optional[Mapping[str, ValueOrFactory]] = None,
):
    """Create the appropriate transport based on transport type."""
    if transport_type == "streamable_http":
        return create_streamable_http_transport(url, headers)
    elif transport_type == "sse":
        return create_sse_transport(url, headers)
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")
