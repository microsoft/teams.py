"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from microsoft_agents.hosting.core.app.agent_application import AgentApplication
from microsoft_agents.hosting.core.authorization.connections import Connections
from microsoft_agents.hosting.core.turn_context import TurnContext
from microsoft_teams.apps import App

from .credentials import make_agent_sdk_token_provider
from .middleware import TeamsMiddleware


def use_teams_sdk(
    app: AgentApplication[Any],
    connection_manager: Connections,
    should_bypass_teams: Optional[Callable[[TurnContext], bool]] = None,
    **teams_app_kwargs: Any,
) -> App:
    reserved = {"client_id", "tenant_id", "token"} & teams_app_kwargs.keys()
    if reserved:
        raise TypeError(f"use_teams_sdk owns {sorted(reserved)}; remove from teams_app_kwargs.")

    auth = connection_manager.get_default_connection_configuration()
    teams_app = App(
        client_id=auth.CLIENT_ID,
        tenant_id=auth.TENANT_ID,
        token=make_agent_sdk_token_provider(connection_manager),
        **teams_app_kwargs,
    )

    app.adapter.use(TeamsMiddleware(teams_app, should_bypass_teams))
    return teams_app
