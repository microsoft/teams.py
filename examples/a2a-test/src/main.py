"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from typing import Annotated, Any, cast

from a2a_utils import extract_cards
from agent_framework import Agent, AgentSession, FunctionInvocationContext, tool
from agent_framework_a2a import A2AAgent  # type: ignore
from agent_framework_openai import OpenAIChatClient
from data_analyst import AGENT_PATH as DATA_ANALYST_PATH
from file_search import agent as file_search_agent
from microsoft_teams.api import Attachment, MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.WARNING)
for _log_name in ("__main__", "data_analyst", "file_search"):
    logging.getLogger(_log_name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)

FILE_DOWNLOAD_CONTENT_TYPE = "application/vnd.microsoft.teams.file.download.info"
DATA_ANALYST_URL = "http://localhost:3979"  # separate process; see data_analyst/__main__.py

ORCHESTRATOR_INSTRUCTIONS = """You are a data assistant in Teams with two tools:
- search_files: reads file attachments (returns file contents as text).
- visualize_data: generates Adaptive Card charts AND tables. This is the ONLY way to display data visually.

Rules:
1. If the user's message (or any prior turn) contains any of these intents — 'chart', 'graph', 'plot',
   'visualize', 'show', 'display', 'table', 'compare', 'trend', 'breakdown', or implies seeing data —
   you MUST call visualize_data. Do not reply with a markdown table or bullet list of data instead.
2. When files arrive, call search_files first to get their contents, then call visualize_data if necessary.
3. visualize_data is stateless — always embed the raw data in each call, do not reference prior calls.
4. Your text reply is a concise summary; no follow-up offers unless there is an error or you need
   more information.
"""


app = App()

_data_analyst_a2a = A2AAgent(url=f"{DATA_ANALYST_URL}{DATA_ANALYST_PATH}/")


# --- Tools exposed to the orchestrator agent ---

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
async def visualize_data(
    analysis_query: Annotated[str, "Raw data plus any analysis instructions to pass to the analyst"],
    context: FunctionInvocationContext,
) -> str:
    """Generate Adaptive Card charts or tables from user-provided data. Always embed raw data in the query."""
    logger.info("visualize_data: query=%r", analysis_query)
    response = await _data_analyst_a2a.run(analysis_query)
    cards = extract_cards(response)
    if context.session is not None:
        context.session.state.setdefault("cards", []).extend(cards)
    logger.info("visualize_data: new_cards=%d", len(cards))
    return f"{len(cards)} chart(s) generated." if cards else (response.text or "No chart generated.")


# --- Orchestrator agent (module-scope: one instance reused across messages) ---

_orchestrator = Agent(
    OpenAIChatClient(),
    instructions=ORCHESTRATOR_INSTRUCTIONS,
    tools=[search_files, visualize_data],
)

_sessions: dict[str, AgentSession] = {}


# --- Teams handler ---


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    files_metadata = _extract_file_attachments(ctx)
    query = ctx.activity.text or ""
    if not query and not files_metadata:
        return

    logger.info("Message received: query=%r, files=%d", query, len(files_metadata))

    if files_metadata:
        query = _inject_file_list(query, files_metadata)

    session = _sessions.setdefault(ctx.activity.conversation.id, AgentSession())
    session.state["cards"] = []

    response = await _orchestrator.run(query, session=session)
    cards: list[dict[str, Any]] = session.state.get("cards", [])

    reply_text = (response.messages[-1].text if response.messages else "") or "Done."
    logger.info("Sending reply + %d adaptive card(s): reply=%r", len(cards), reply_text)
    await ctx.reply(reply_text)

    for card_dict in cards:
        await ctx.send(
            MessageActivityInput().add_attachments(
                Attachment(content_type="application/vnd.microsoft.card.adaptive", content=card_dict)
            )
        )


def _extract_file_attachments(ctx: ActivityContext[MessageActivity]) -> list[dict[str, Any]]:
    """Pull (name, download_url) for each Teams file.download.info attachment."""
    out: list[dict[str, Any]] = []
    for a in ctx.activity.attachments or []:
        if a.content_type != FILE_DOWNLOAD_CONTENT_TYPE:
            continue
        content = cast(dict[str, Any], a.content) if isinstance(a.content, dict) else {}  # pyright: ignore[reportUnknownMemberType]
        url = content.get("downloadUrl")
        if isinstance(url, str) and url:
            out.append({"name": a.name, "download_url": url})
    return out


def _inject_file_list(query: str, files_metadata: list[dict[str, Any]]) -> str:
    """Prepend the file list to the user's query so the LLM can forward it to search_files."""
    file_list = "\n".join(f"- name: {f['name']}, download_url: {f['download_url']}" for f in files_metadata)
    prefix = f"Files available (pass this list to search_files when you call it):\n{file_list}\n\n"
    return prefix + (query or "Summarize the files and generate relevant data insights.")


if __name__ == "__main__":
    asyncio.run(app.start())
