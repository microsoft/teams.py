"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Annotated

from agent_framework import Agent, FunctionInvocationContext, tool
from agent_framework_openai import OpenAIChatClient
from analyst_client import ask as ask_data_analyst
from file_search import agent as file_search_agent
from prompts import ORCHESTRATOR_INSTRUCTIONS

logger = logging.getLogger(__name__)

DATA_ANALYST_URL = "http://localhost:3979"  # separate process; see data_analyst/__main__.py


search_files = file_search_agent.as_tool(
    name="search_files",
    description=(
        "Read and search through file attachments shared in this Teams conversation. "
        "The task MUST include the list of available files (names and download URLs), "
        "e.g. 'Available files:\\n- name: sales.csv, download_url: https://...\\n\\nQuery: which month...'."
    ),
    arg_name="search_query",
    arg_description="Question to answer from the shared files, including the file list and URLs.",
)


@tool
async def ask_analyst(
    analysis_query: Annotated[str, "Instruction for the analyst; include raw data if it's new"],
    context: FunctionInvocationContext,
) -> str:
    """Ask the data-analyst agent for analysis or a visualization.

    The analyst has per-conversation memory, so follow-ups in the same conversation can reference
    earlier data without re-pasting it.
    """
    logger.info("ask_analyst: query=%r", analysis_query)
    # Stable A2A context_id = Teams conversation id → analyst keeps a per-conversation session.
    conv_id = context.session.state.get("teams_conversation_id") if context.session else None
    cards, text = await ask_data_analyst(DATA_ANALYST_URL, analysis_query, conv_id)
    if context.session is not None and cards:
        context.session.state.setdefault("cards", []).extend(cards)
    logger.info("ask_analyst: new_cards=%d", len(cards))
    return f"{len(cards)} chart(s) generated." if cards else (text or "No chart generated.")


orchestrator = Agent(
    OpenAIChatClient(),
    instructions=ORCHESTRATOR_INSTRUCTIONS,
    tools=[search_files, ask_analyst],
)
