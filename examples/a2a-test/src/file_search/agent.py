"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import uuid
from typing import Annotated, Any, cast

import httpx
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Message, Part, Role, TextPart
from agent_framework import Agent, tool
from agent_framework_openai import OpenAIChatClient
from fastapi import FastAPI

logger = logging.getLogger(__name__)

AGENT_PATH = "/file-search"

INSTRUCTIONS = (
    "You are a file search assistant. "
    "The user will provide a list of available files (name + download URL) and a query. "
    "Download only the files that are likely relevant to the query, then answer based on their contents.\n\n"
    "When returning tabular data (CSV rows, records, etc.), reproduce EVERY row verbatim — "
    "do not summarize, sample, or use '...' to elide rows. Downstream tools will chart or tabulate "
    "the data and need complete rows."
)


@tool
async def download_file(
    name: Annotated[str, "The filename as it appears in the metadata"],
    download_url: Annotated[str, "The pre-authenticated download URL for the file"],
) -> str:
    """Download a file and return its text content."""
    logger.info("download_file: name=%r", name)
    async with httpx.AsyncClient() as http:
        response = await http.get(download_url)
        response.raise_for_status()
        content = response.content.decode("utf-8", errors="replace")
        logger.info("download_file: name=%r, size=%d bytes", name, len(content))
        return content


class FileSearchAgentExecutor(AgentExecutor):
    """A2A executor that runs an Agent with a download_file tool to read and summarize attachments."""

    def __init__(self) -> None:
        self._agent = Agent(OpenAIChatClient(), instructions=INSTRUCTIONS, tools=[download_file])

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_message = self._build_user_message(context)
        if user_message is None:
            await self._reply(event_queue, context, "No files provided.")
            return

        response = await self._agent.run(user_message)
        await self._reply(event_queue, context, response.text or "No response.")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass

    @staticmethod
    def _build_user_message(context: RequestContext) -> str | None:
        """Assemble the query string for the inner Agent from A2A parts.

        Supports two input shapes:
        - TextPart only: the caller has already embedded file list + query in the text.
        - DataPart with {"files": [...]} + optional TextPart query.
        """
        query = ""
        files_metadata: list[dict[str, Any]] = []

        for part in context.message.parts if context.message else []:
            inner = part.root
            if inner.kind == "text":
                query = inner.text
            elif inner.kind == "data":
                files = inner.data.get("files", [])
                if isinstance(files, list):
                    files_metadata = [cast(dict[str, Any], f) for f in files if isinstance(f, dict)]  # pyright: ignore[reportUnknownVariableType]

        if files_metadata:
            file_list = "\n".join(
                f"- name: {f.get('name', 'unknown')}, download_url: {f.get('download_url', '')}" for f in files_metadata
            )
            return f"Available files:\n{file_list}\n\nQuery: {query or 'Summarize the contents of these files.'}"
        return query or None

    @staticmethod
    async def _reply(event_queue: EventQueue, context: RequestContext, text: str) -> None:
        await event_queue.enqueue_event(
            Message(
                kind="message",
                message_id=str(uuid.uuid4()),
                role=Role("agent"),
                parts=[Part(root=TextPart(kind="text", text=text))],
                context_id=context.context_id,
            )
        )


def _agent_card(base_url: str) -> AgentCard:
    return AgentCard(
        name="File Search Agent",
        description="Downloads Teams file attachments and answers queries about their content.",
        url=f"{base_url}{AGENT_PATH}",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="file_search",
                name="File Search",
                description="Reads file attachments shared in Teams and extracts relevant info from them.",
                tags=["file", "search", "teams"],
            )
        ],
    )


def build_app(base_url: str) -> FastAPI:
    """Build the FastAPI app hosting the file-search A2A server."""
    a2a_app = A2AFastAPIApplication(
        agent_card=_agent_card(base_url),
        http_handler=DefaultRequestHandler(
            agent_executor=FileSearchAgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    return a2a_app.build()
