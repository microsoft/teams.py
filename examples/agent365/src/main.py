"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from urllib.parse import urlparse

from microsoft.opentelemetry.a365.core import (
    AgentDetails,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    Request,
    ServiceEndpoint,
)
from microsoft_teams.api import (
    AgenticUserDeletedActivity,
    AgenticUserDisabledActivity,
    AgenticUserEnabledActivity,
    AgenticUserIdentityCreatedActivity,
    AgenticUserIdentityUpdatedActivity,
    AgenticUserManagerUpdatedActivity,
    AgenticUserUndeletedActivity,
    AgenticUserWorkloadOnboardingUpdatedActivity,
    AgentLifecycleEventActivity,
    MessageActivity,
)
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, Agent365BaggageOptions, App
from observability import Agent365TokenCache, use_agent365_exporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent365: Agent365BaggageOptions = {
    "include": ["senderName", "senderEmail", "agentName", "agentEmail", "agentDescription"],
    "operation_source": "Microsoft.Teams.Apps",
}
app = App(telemetry={"agent365": agent365})
token_cache = Agent365TokenCache()
use_agent365_exporter(token_cache)


def _log_lifecycle_envelope(activity: AgentLifecycleEventActivity, handler_name: str) -> None:
    logger.info(
        "[Agent365 lifecycle:%s] name=%s value_type=%s event_type=%s channel_id=%s from=%s recipient_identity=%s",
        handler_name,
        activity.name,
        activity.value_type,
        activity.value.event_type,
        activity.channel_id,
        activity.from_.id,
        activity.recipient.agentic_user,
    )
    logger.info(
        "[Agent365 lifecycle:%s] tenant_id=%s agentic_user_id=%s app_instance_id=%s blueprint_id=%s version=%s",
        handler_name,
        activity.value.tenant_id,
        activity.value.agentic_user_id,
        activity.value.agentic_app_instance_id,
        activity.value.agentic_blueprint_id,
        activity.value.version,
    )


@app.on_agent_lifecycle
async def handle_agent_lifecycle(ctx: ActivityContext[AgentLifecycleEventActivity]) -> None:
    """Log every Agent 365 agentLifecycle event."""
    _log_lifecycle_envelope(ctx.activity, "all")
    await ctx.next()


@app.on_agentic_user_identity_created
async def handle_agentic_user_identity_created(ctx: ActivityContext[AgenticUserIdentityCreatedActivity]) -> None:
    """Log an agentic user identity creation event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "identity_created")
    logger.info(
        "[Agent365 lifecycle:identity_created] expiration_date_time=%s manager=%s",
        activity.value.expiration_date_time,
        activity.value.manager,
    )


@app.on_agentic_user_identity_updated
async def handle_agentic_user_identity_updated(ctx: ActivityContext[AgenticUserIdentityUpdatedActivity]) -> None:
    """Log an agentic user identity property update event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "identity_updated")
    logger.info(
        "[Agent365 lifecycle:identity_updated] updated_property=%s",
        activity.value.updated_property,
    )


@app.on_agentic_user_manager_updated
async def handle_agentic_user_manager_updated(ctx: ActivityContext[AgenticUserManagerUpdatedActivity]) -> None:
    """Log an agentic user manager update event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "manager_updated")
    logger.info("[Agent365 lifecycle:manager_updated] manager=%s", activity.value.manager)


@app.on_agentic_user_enabled
async def handle_agentic_user_enabled(ctx: ActivityContext[AgenticUserEnabledActivity]) -> None:
    """Log an agentic user enabled event."""
    _log_lifecycle_envelope(ctx.activity, "enabled")


@app.on_agentic_user_disabled
async def handle_agentic_user_disabled(ctx: ActivityContext[AgenticUserDisabledActivity]) -> None:
    """Log an agentic user disabled event."""
    _log_lifecycle_envelope(ctx.activity, "disabled")


@app.on_agentic_user_deleted
async def handle_agentic_user_deleted(ctx: ActivityContext[AgenticUserDeletedActivity]) -> None:
    """Log an agentic user deleted event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "deleted")
    logger.info("[Agent365 lifecycle:deleted] deletion_reason=%s", activity.value.deletion_reason)


@app.on_agentic_user_undeleted
async def handle_agentic_user_undeleted(ctx: ActivityContext[AgenticUserUndeletedActivity]) -> None:
    """Log an agentic user undeleted event."""
    _log_lifecycle_envelope(ctx.activity, "undeleted")


@app.on_agentic_user_workload_onboarding_updated
async def handle_agentic_user_workload_onboarding_updated(
    ctx: ActivityContext[AgenticUserWorkloadOnboardingUpdatedActivity],
) -> None:
    """Log an agentic user workload onboarding update event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "workload_onboarding_updated")
    logger.info(
        "[Agent365 lifecycle:workload_onboarding_updated] workload_name=%s workload_onboarding_state=%s",
        activity.value.workload_name,
        activity.value.workload_onboarding_state,
    )


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Echo incoming messages using the inbound AgenticUser when present."""
    logger.info(
        "[Agent365 reactive] activity_id=%s conversation_id=%s from_id=%s recipient_id=%s",
        ctx.activity.id,
        ctx.activity.conversation.id,
        ctx.activity.from_.id,
        ctx.activity.recipient.id,
    )

    agentic_user = ctx.activity.recipient.agentic_user
    if agentic_user is None or agentic_user.tenant_id is None:
        logger.warning("No Agent365 user on the activity; handling without an InvokeAgent scope")
        await _handle_message(ctx)
        return

    await token_cache.refresh(
        app.token_provider,
        agentic_user.agentic_app_instance_id,
        agentic_user.tenant_id,
    )
    parsed_service_url = urlparse(ctx.activity.service_url or "")
    endpoint = (
        ServiceEndpoint(str(parsed_service_url.hostname), parsed_service_url.port)
        if parsed_service_url.hostname
        else None
    )
    with InvokeAgentScope.start(
        Request(conversation_id=ctx.activity.conversation.id),
        InvokeAgentScopeDetails(endpoint=endpoint),
        AgentDetails(
            agent_id=agentic_user.agentic_app_instance_id,
            agentic_user_id=agentic_user.agentic_user_id,
            agent_blueprint_id=agentic_user.agentic_blueprint_id,
            tenant_id=agentic_user.tenant_id,
        ),
    ):
        await _handle_message(ctx)


async def _handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    await ctx.reply(TypingActivityInput())
    text = ctx.activity.text.lower()

    if "react" in text:
        await ctx.api.conversations.add_reaction(
            conversation_id=ctx.activity.conversation.id,
            activity_id=ctx.activity.id,
            reaction_type="like",
        )
        await ctx.reply("Added a like reaction to your message.")
        return

    if "reply" in text:
        await ctx.reply("Hello! How can I assist you today?")
    else:
        await ctx.send(f"You said '{ctx.activity.text}'")


if __name__ == "__main__":
    asyncio.run(app.start())
