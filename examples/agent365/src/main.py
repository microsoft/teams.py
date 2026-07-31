"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import re

from microsoft_teams.api import (
    AgenticIdentityCreatedActivity,
    AgenticIdentityDeletedActivity,
    AgenticIdentityDisabledActivity,
    AgenticIdentityEnabledActivity,
    AgenticIdentityManagerUpdatedActivity,
    AgenticIdentityUndeletedActivity,
    AgenticIdentityUpdatedActivity,
    AgenticIdentityWorkloadOnboardingUpdatedActivity,
    AgentLifecycleEventActivity,
    MessageActivity,
)
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App()


def _log_lifecycle_envelope(activity: AgentLifecycleEventActivity, handler_name: str) -> None:
    logger.info(
        "[Agent365 lifecycle:%s] name=%s value_type=%s event_type=%s channel_id=%s from=%s recipient_identity=%s",
        handler_name,
        activity.name,
        activity.value_type,
        activity.value.event_type,
        activity.channel_id,
        activity.from_.id,
        activity.recipient.agentic_identity,
    )
    logger.info(
        "[Agent365 lifecycle:%s] tenant_id=%s agentic_user_id=%s agentic_app_id=%s app_blueprint_id=%s version=%s",
        handler_name,
        activity.value.tenant_id,
        activity.value.agentic_user_id,
        activity.value.agentic_app_id,
        activity.value.agentic_app_blueprint_id,
        activity.value.version,
    )


@app.on_agent_lifecycle
async def handle_agent_lifecycle(ctx: ActivityContext[AgentLifecycleEventActivity]) -> None:
    """Log every Agent 365 agentLifecycle event."""
    _log_lifecycle_envelope(ctx.activity, "all")
    await ctx.next()


@app.on_agentic_identity_created
async def handle_agentic_identity_created(ctx: ActivityContext[AgenticIdentityCreatedActivity]) -> None:
    """Log an agentic identity creation event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "identity_created")
    logger.info(
        "[Agent365 lifecycle:identity_created] expiration_date_time=%s manager=%s",
        activity.value.expiration_date_time,
        activity.value.manager,
    )


@app.on_agentic_identity_updated
async def handle_agentic_identity_updated(ctx: ActivityContext[AgenticIdentityUpdatedActivity]) -> None:
    """Log an agentic identity property update event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "identity_updated")
    logger.info(
        "[Agent365 lifecycle:identity_updated] updated_property=%s",
        activity.value.updated_property,
    )


@app.on_agentic_identity_manager_updated
async def handle_agentic_identity_manager_updated(ctx: ActivityContext[AgenticIdentityManagerUpdatedActivity]) -> None:
    """Log an agentic identity manager update event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "manager_updated")
    logger.info("[Agent365 lifecycle:manager_updated] manager=%s", activity.value.manager)


@app.on_agentic_identity_enabled
async def handle_agentic_identity_enabled(ctx: ActivityContext[AgenticIdentityEnabledActivity]) -> None:
    """Log an agentic identity enabled event."""
    _log_lifecycle_envelope(ctx.activity, "enabled")


@app.on_agentic_identity_disabled
async def handle_agentic_identity_disabled(ctx: ActivityContext[AgenticIdentityDisabledActivity]) -> None:
    """Log an agentic identity disabled event."""
    _log_lifecycle_envelope(ctx.activity, "disabled")


@app.on_agentic_identity_deleted
async def handle_agentic_identity_deleted(ctx: ActivityContext[AgenticIdentityDeletedActivity]) -> None:
    """Log an agentic identity deleted event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "deleted")
    logger.info("[Agent365 lifecycle:deleted] deletion_reason=%s", activity.value.deletion_reason)


@app.on_agentic_identity_undeleted
async def handle_agentic_identity_undeleted(ctx: ActivityContext[AgenticIdentityUndeletedActivity]) -> None:
    """Log an agentic identity undeleted event."""
    _log_lifecycle_envelope(ctx.activity, "undeleted")


@app.on_agentic_identity_workload_onboarding_updated
async def handle_agentic_identity_workload_onboarding_updated(
    ctx: ActivityContext[AgenticIdentityWorkloadOnboardingUpdatedActivity],
) -> None:
    """Log an agentic identity workload onboarding update event."""
    activity = ctx.activity
    _log_lifecycle_envelope(activity, "workload_onboarding_updated")
    logger.info(
        "[Agent365 lifecycle:workload_onboarding_updated] workload_name=%s workload_onboarding_state=%s",
        activity.value.workload_name,
        activity.value.workload_onboarding_state,
    )


@app.on_message_pattern(re.compile(r"hello|hi|greetings"))
async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle greeting messages using the inbound AgenticIdentity when present."""
    await ctx.reply("Hello! How can I assist you today?")


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Echo incoming messages using the inbound AgenticIdentity when present."""
    logger.info("[Agent365 reactive] Message received: %s", ctx.activity.text)
    logger.info("[Agent365 reactive] From: %s", ctx.activity.from_)
    logger.info("[Agent365 reactive] AgenticIdentity: %s", ctx.activity.recipient.agentic_identity)

    await ctx.reply(TypingActivityInput())

    if "react" in ctx.activity.text.lower():
        await ctx.api.conversations.add_reaction(
            conversation_id=ctx.activity.conversation.id,
            activity_id=ctx.activity.id,
            reaction_type="like",
        )
        await ctx.reply("Added a like reaction to your message.")
        return

    if "reply" in ctx.activity.text.lower():
        await ctx.reply("Hello! How can I assist you today?")
    else:
        await ctx.send(f"You said '{ctx.activity.text}'")


if __name__ == "__main__":
    asyncio.run(app.start())
