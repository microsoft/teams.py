"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from os import getenv
from pathlib import Path
from typing import Any

from agent_framework import Agent, FunctionInvocationContext, FunctionMiddleware
from agent_framework.foundry import FoundryChatClient
from azure.identity import ClientSecretCredential
from dotenv import find_dotenv, load_dotenv
from local_tools import tools as local_tools
from mcp_tools import mcp_tools

load_dotenv(find_dotenv(usecwd=True))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AgentMiddleware(FunctionMiddleware):
    """Logs every tool call and extracts MCP citations from results.

    citations is reset at the start of each message turn and populated as tools run.
    Only URLs from results matching { results: [{ contentUrl, title, content }] } are collected.
    """

    citations: dict[str, Any]

    async def process(self, context: FunctionInvocationContext, call_next: Callable[[], Awaitable[None]]) -> None:
        logger.info("tool call: %s(%s)", context.function.name, context.arguments)
        await call_next()
        result: Any = context.result
        if isinstance(result, list):
            result = " ".join(str(getattr(c, "text", c)) for c in result if getattr(c, "text", None))  # type: ignore
        logger.info("tool result: %s -> %s", context.function.name, result)

        try:
            parsed = json.loads(str(result))
            for item in parsed.get("results", []):
                url = item.get("contentUrl") or item.get("link")
                if url:
                    title = item.get("title") or ""
                    snippet = (item.get("content") or item.get("description") or "")[:160]
                    self.citations.setdefault(url, {"url": url, "title": title, "snippet": snippet})
        except Exception:
            pass


def _require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"Required environment variable {name!r} is not set.")
    return value


client = FoundryChatClient(
    project_endpoint=_require_env("PROJECT_ENDPOINT"),
    model=_require_env("AZURE_OPENAI_MODEL"),
    credential=ClientSecretCredential(
        tenant_id=_require_env("TENANT_ID"),
        client_id=_require_env("CLIENT_ID"),
        client_secret=_require_env("CLIENT_SECRET"),
    ),
)

tool_logger = AgentMiddleware()
agent = Agent(
    client=client,
    instructions=(Path(__file__).parent / "instructions.txt").read_text(),
    tools=[*local_tools, *mcp_tools],
    middleware=[tool_logger],
)
