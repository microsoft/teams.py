"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from os import getenv
from typing import Any, cast

from agent_framework import Agent, FunctionInvocationContext, FunctionMiddleware
from agent_framework.openai import OpenAIChatClient
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
            blocks = cast("list[Any]", result)
            result = " ".join(str(c.text) for c in blocks if getattr(c, "text", None))
        logger.info("tool result: %s -> %s", context.function.name, result)

        try:
            parsed = json.loads(result)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("citation extraction skipped for %s: %s", context.function.name, e)
            return
        if not isinstance(parsed, dict):
            return
        parsed = cast("dict[str, Any]", parsed)

        for item in cast("list[dict[str, Any]]", parsed.get("results", [])):
            url = item.get("contentUrl") or item.get("link")
            if not url:
                continue
            entry = self.citations.setdefault(
                url,
                {
                    "position": len(self.citations) + 1,
                    "url": url,
                    "title": item.get("title") or "",
                    "snippet": (item.get("content") or item.get("description") or "")[:160],
                },
            )
            item["citation"] = f"[{entry['position']}]"
        context.result = json.dumps(parsed)


def _require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"Required environment variable {name!r} is not set.")
    return value


client = OpenAIChatClient(
    model=_require_env("AZURE_OPENAI_MODEL"),
    azure_endpoint=_require_env("AZURE_OPENAI_ENDPOINT"),
    api_key=_require_env("AZURE_OPENAI_API_KEY"),
)

INSTRUCTIONS = """\
You are a helpful Teams assistant with access to local tools and remote MCP servers.

When you use information from a search tool, cite your sources inline using the "citation" value \
provided in each result (e.g. [1], [2]).
Do not add a references or sources list at the end of your response — citations are displayed separately in the UI.
"""

tool_logger = AgentMiddleware()
agent = Agent(
    client=client,
    instructions=INSTRUCTIONS,
    tools=[*local_tools, *mcp_tools],
    middleware=[tool_logger],
)
