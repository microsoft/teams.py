"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from os import getenv
from pathlib import Path
from typing import Any, cast

from agent_framework import Agent, FunctionInvocationContext, FunctionMiddleware
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from local_tools import tools as local_tools
from mcp_tools import mcp_tools

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AgentMiddleware(FunctionMiddleware):
    """Logs every tool call and extracts MCP citations from results.

    citations is reset at the start of each message turn and populated as tools run.
    Only URLs from results matching { results: [{ contentUrl, title, content }] } are collected.
    """

    citations: dict[str, Any]

    async def process(self, context: FunctionInvocationContext, call_next: Callable[[], Awaitable[None]]) -> None:
        args = dict(context.arguments) if hasattr(context.arguments, "__iter__") else context.arguments
        logger.info("tool call: %s(%s)", context.function.name, args)
        await call_next()
        result: Any = context.result
        if isinstance(result, list):
            items = cast(list[Any], result)
            result = " ".join(str(getattr(c, "text", c)) for c in items if getattr(c, "text", None))
        logger.info("tool result: %s -> %s", context.function.name, result)

        try:
            for item in json.loads(str(result)).get("results", []):
                url = item.get("contentUrl") or item.get("link")
                if url:
                    title = item.get("title") or ""
                    snippet = (item.get("content") or item.get("description") or "")[:160]
                    self.citations.setdefault(url, {"url": url, "title": title, "snippet": snippet})
        except Exception:
            pass


# DefaultAzureCredential tries in order: env vars (AZURE_CLIENT_ID/SECRET/TENANT_ID),
# workload identity, managed identity, az login, azd auth login.
client = FoundryChatClient(
    project_endpoint=getenv("PROJECT_ENDPOINT"),
    model=getenv("AZURE_OPENAI_MODEL"),
    credential=DefaultAzureCredential(),
)

tool_logger = AgentMiddleware()
agent = Agent(
    client=client,
    instructions=(Path(__file__).parent / "instructions.txt").read_text(),
    tools=[*local_tools, *mcp_tools],
    middleware=[tool_logger],
)
