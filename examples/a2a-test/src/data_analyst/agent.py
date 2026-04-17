"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import uuid
from typing import Annotated, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, DataPart, Message, Part, Role, TextPart
from agent_framework import Agent, tool
from agent_framework_openai import OpenAIChatClient
from fastapi import FastAPI

from .cards import AdaptiveCard, ChartType, build_card

logger = logging.getLogger(__name__)

AGENT_PATH = "/data-analyst"

SYSTEM_PROMPT = """You are an expert data analyst. When the user provides data, produce a visualization.

Call generate_card once per visualization the user asks for, then reply with a one-sentence summary.

Data row format:
- For chart types (verticalBar, horizontalBar, line, pie): pass data rows as [label, numeric_value] pairs ONLY.
  Do NOT include a header row. Numeric values must be numbers, not strings with currency symbols.
- For table: include the header row as the first row; subsequent rows are data.

Only use data explicitly provided — never invent values. If no data is provided, ask the user to share some.
"""


class DataAnalystAgentExecutor(AgentExecutor):
    """A2A executor: runs an Agent with a generate_card tool, emits built cards as a DataPart."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input() if context.message else ""
        logger.info("DataAnalyst executing: query=%r", query)

        card_holder: list[AdaptiveCard] = []

        @tool
        def generate_card(
            chart_type: Annotated[ChartType, "Type of chart or table to render"],
            rows: Annotated[list[list[Any]], "2D data rows; first row is headers for tables"],
            options: Annotated[dict[str, Any] | None, "Optional: title, xAxisTitle, yAxisTitle"] = None,
        ) -> str:
            """Build an Adaptive Card visualization from the provided data."""
            logger.info("generate_card: type=%s, rows=%d", chart_type, len(rows))
            card_holder.append(build_card(chart_type, rows, options))
            return f"Generated a {chart_type} chart with {len(rows)} data point(s)."

        agent = Agent(OpenAIChatClient(), instructions=SYSTEM_PROMPT, tools=[generate_card])
        response = await agent.run(query)
        logger.info("DataAnalyst done: summary=%r, cards=%d", response.text, len(card_holder))

        if card_holder:
            card_dicts = [c.model_dump(by_alias=True, exclude_none=True) for c in card_holder]
            parts: list[Part] = [Part(root=DataPart(kind="data", data={"cards": card_dicts}))]
        else:
            parts = [Part(root=TextPart(kind="text", text=response.text or "No card generated."))]

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
        name="Data Analyst Agent",
        description="Generate Adaptive Card charts and tables from data.",
        url=f"{base_url}{AGENT_PATH}/",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id="data_analysis",
                name="Data Analysis",
                description="Generate Adaptive Card charts and tables from data.",
                tags=["data", "charts", "analytics"],
            )
        ],
    )


def build_app(base_url: str) -> FastAPI:
    """Build the FastAPI app hosting the data-analyst A2A server."""
    a2a_app = A2AFastAPIApplication(
        agent_card=_agent_card(base_url),
        http_handler=DefaultRequestHandler(
            agent_executor=DataAnalystAgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    return a2a_app.build()
