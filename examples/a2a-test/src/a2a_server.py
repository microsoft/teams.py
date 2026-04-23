"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a_executor import AskReplyExecutor
from microsoft_teams.apps import App
from state import BotState


def make_a2a_app(
    *,
    teams_app: App,
    state: BotState,
    description: str,
    skill: str,
    url: str,
    allowed_peer_urls: list[str],
) -> A2AStarletteApplication:
    # Builds the A2A server for this bot: an AgentCard advertising the
    # skill at `url`, plus a request handler wired to AskReplyExecutor
    # which dispatches incoming asks/replies into the Teams app.
    agent_card = AgentCard(
        name=state.name,
        description=description,
        url=url,
        version="1.0.0",
        protocol_version="0.3.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[AgentSkill(id=skill, name=skill, description=description, tags=[skill])],
    )
    handler = DefaultRequestHandler(
        agent_executor=AskReplyExecutor(teams_app=teams_app, state=state, allowed_peer_urls=allowed_peer_urls),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
