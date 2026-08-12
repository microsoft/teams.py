"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional, cast

from microsoft_agents.activity import Activity, ActivityTypes, InvokeResponse
from microsoft_agents.hosting.core.middleware_set import Middleware
from microsoft_agents.hosting.core.turn_context import TurnContext
from microsoft_teams.api import ActivityTypeAdapter
from microsoft_teams.apps import App
from microsoft_teams.apps.events.types import ActivityEvent, CoreActivity

from .context import agent_sdk_context
from .token import TeamsToken

TEAMS_CHANNEL_ID = "msteams"


def is_teams_channel(activity: Activity) -> bool:
    """True for Teams turns, including sub-channels like ``msteams:COPILOT``."""
    channel_id: Optional[str] = activity.channel_id
    if not channel_id:
        return False

    channel = getattr(channel_id, "channel", None)
    if channel is None:
        channel = str(channel_id).split(":", 1)[0]
    return channel == TEAMS_CHANNEL_ID


class TeamsMiddleware(Middleware):
    def __init__(
        self,
        teams_app: App,
        should_bypass_teams: Optional[Callable[[TurnContext], bool]] = None,
    ) -> None:
        self._teams_app = teams_app
        self._should_bypass_teams = should_bypass_teams

    async def on_turn(
        self,
        context: TurnContext,
        logic: Callable[[TurnContext], Awaitable[None]],
    ) -> None:
        activity: Activity = context.activity
        if not is_teams_channel(activity):
            await logic(context)
            return

        # Idempotent — App tracks _initialized internally. Run on every Teams
        # turn so AgentApplication handlers can safely call into TEAMS_APP
        # (e.g. ``TEAMS_APP.send`` for proactive sends) even when no teams.py
        # route matched this turn.
        await self._teams_app.initialize()

        if self._should_bypass_teams is not None and self._should_bypass_teams(context):
            await logic(context)
            return

        core_activity = self._translate_inbound(activity)

        if not self._teams_app.router.select_handlers(core_activity):
            # No teams.py route matches; let AgentApplication try its handlers.
            await logic(context)
            return

        event = ActivityEvent(
            body=cast(CoreActivity, core_activity),
            token=TeamsToken.from_activity(activity),
        )

        ctx_token = agent_sdk_context.set(context)
        try:
            invoke_response = await self._teams_app.activity_processor.process_activity(plugins=[], event=event)
        finally:
            agent_sdk_context.reset(ctx_token)

        if activity.type == ActivityTypes.invoke:
            await self._propagate_invoke_response(context, invoke_response)

    @staticmethod
    def _translate_inbound(activity: Activity):
        payload: str = activity.model_dump_json(by_alias=True, exclude_none=True)
        return ActivityTypeAdapter.validate_json(payload)

    @staticmethod
    async def _propagate_invoke_response(context: TurnContext, invoke_response: object) -> None:
        if invoke_response is None:
            return

        status: Any
        body: Any
        if isinstance(invoke_response, dict):
            response = cast("dict[str, Any]", invoke_response)
            status = response.get("status")
            body = response.get("body")
        else:
            status = getattr(invoke_response, "status", None)
            body = getattr(invoke_response, "body", None)

        if status is None:
            return

        if hasattr(body, "model_dump"):
            body = body.model_dump(mode="json", by_alias=True, exclude_none=True)

        await context.send_activity(
            Activity(
                type=ActivityTypes.invoke_response,
                value=InvokeResponse(status=status, body=body),
            )
        )
