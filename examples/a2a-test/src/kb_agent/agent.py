"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import os
import uuid
from typing import Annotated, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, DataPart, Message, Part, Role, TextPart
from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import ClientSecretCredential
from fastapi import FastAPI

from .cards import ChartType, build_answer_card, build_chart_card
from .index import KBIndex
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

AGENT_PATH = "/kb-agent"

_INDEX = KBIndex()


class KBAgentExecutor(AgentExecutor):
    """A2A executor: stateless per request — runs an Agent over the KB and returns Adaptive Cards."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input() if context.message else ""
        logger.info("KBAgent executing: ctx=%r query=%r", context.context_id, query)

        card_holder: list[dict[str, Any]] = []

        @tool
        async def search_kb(
            search_query: Annotated[str, "Search query for the knowledge base"],
            k: Annotated[int, "Number of results to return"] = 3,
        ) -> list[dict[str, str]]:
            """Search the knowledge base. Returns top-k hits with id, title, source, and snippet."""
            hits = await _INDEX.search(search_query, k=k)
            logger.info("search_kb: q=%r hits=%d", search_query, len(hits))
            return [{"id": d.id, "title": d.title, "source": d.source, "snippet": d.snippet} for d in hits]

        @tool
        async def render_answer(
            answer: Annotated[str, "Final answer synthesized from retrieved snippets"],
            source_ids: Annotated[list[str], "IDs of KB docs that actually support the answer"],
        ) -> str:
            """Render the final answer as an Adaptive Card with cited sources."""
            resolved = [await _INDEX.get(sid) for sid in source_ids]
            sources = [d for d in resolved if d is not None]
            card = build_answer_card(answer, sources)
            card_holder.append(card.model_dump(by_alias=True, exclude_none=True))
            logger.info("render_answer: sources=%d", len(sources))
            return f"Rendered answer with {len(sources)} source(s)."

        @tool
        async def render_chart(
            chart_type: Annotated[ChartType, "verticalBar, horizontalBar, line, pie, or table"],
            rows: Annotated[list[list[Any]], "2D data rows; first row is headers for tables"],
            title: Annotated[str, "Chart title"],
            source_ids: Annotated[list[str] | None, "IDs of KB docs the data came from"] = None,
        ) -> str:
            """Render a chart or table Adaptive Card with optional cited sources."""
            ids = source_ids or []
            resolved = [await _INDEX.get(sid) for sid in ids]
            sources = [d for d in resolved if d is not None]
            card = build_chart_card(chart_type, rows, title, sources)
            card_holder.append(card.model_dump(by_alias=True, exclude_none=True))
            logger.info("render_chart: type=%s rows=%d sources=%d", chart_type, len(rows), len(sources))
            return f"Rendered {chart_type} with {len(rows)} row(s)."

        agent = Agent(
            FoundryChatClient(
                credential=ClientSecretCredential(
                    tenant_id=os.environ["TENANT_ID"],
                    client_id=os.environ["CLIENT_ID"],
                    client_secret=os.environ["CLIENT_SECRET"],
                ),
            ),
            instructions=SYSTEM_PROMPT,
            tools=[search_kb, render_answer, render_chart],
        )
        response = await agent.run(query)
        logger.info("KBAgent done: summary=%r, cards=%d", response.text, len(card_holder))

        if card_holder:
            parts: list[Part] = [Part(root=DataPart(kind="data", data={"cards": card_holder}))]
        else:
            parts = [Part(root=TextPart(kind="text", text=response.text or "No answer rendered."))]

        await event_queue.enqueue_event(
            Message(
                kind="message",
                message_id=str(uuid.uuid4()),
                role=Role("agent"),
                parts=parts,
                context_id=context.context_id,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def _agent_card(base_url: str) -> AgentCard:
    return AgentCard(
        name="Northwind KB Agent",
        description="Answers questions about Northwind Co. internal policies and handbooks.",
        url=f"{base_url}{AGENT_PATH}/",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id="kb_qa",
                name="Knowledge Base QA",
                description="Retrieves and synthesizes answers from internal docs with citations.",
                tags=["knowledge-base", "qa", "retrieval"],
            )
        ],
    )


def build_app(base_url: str) -> FastAPI:
    """Build the FastAPI app hosting the KB-agent A2A server."""
    a2a_app = A2AFastAPIApplication(
        agent_card=_agent_card(base_url),
        http_handler=DefaultRequestHandler(
            agent_executor=KBAgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    return a2a_app.build()
