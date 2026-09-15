"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from collections.abc import Awaitable, Callable
from typing import Optional

from microsoft_teams.api import AgenticIdentity, TokenProtocol

from .files.download import GraphCredential
from .files.errors import FileActor


def select_files_credential(
    *,
    agentic_identity: Optional[AgenticIdentity],
    graph_base_url_root: Optional[str],
    get_app_graph_token: Callable[[], Awaitable[Optional[TokenProtocol]]],
    get_agentic_graph_token: Callable[[AgenticIdentity], Awaitable[Optional[TokenProtocol]]],
) -> GraphCredential:
    """
    Choose which identity reads a file's bytes, for the current inbound activity.

    An Agentic User reads as itself, never the app token: an app-only token sees what the app may read tenant-wide, a
    different set from what was shared with the agent, so it would 403 on exactly the files the agent was given.

    The token is resolved lazily, so a turn that never touches files never acquires one.
    """

    # Only the actor and how its token is fetched vary. Building the rest here means a new actor is one arm rather
    # than a third copy of the whole credential, and cannot silently omit the host root.
    def _as(actor: FileActor, token: Callable[[], Awaitable[Optional[str]]]) -> GraphCredential:
        return GraphCredential(actor=actor, token=token, base_url_root=graph_base_url_root)

    if agentic_identity is not None:
        identity = agentic_identity

        async def agentic_token() -> Optional[str]:
            token = await get_agentic_graph_token(identity)
            return str(token) if token else None

        return _as("agentic_user", agentic_token)

    async def app_token() -> Optional[str]:
        token = await get_app_graph_token()
        return str(token) if token else None

    return _as("app", app_token)
