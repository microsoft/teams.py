"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import (
    ActivityParams,
    AgenticIdentity,
    ApiClient,
    ConversationReference,
    MessageActivityInput,
    SentActivity,
)


async def send_or_update_activity(
    api: ApiClient,
    activity: ActivityParams,
    ref: ConversationReference,
    *,
    agentic_identity: AgenticIdentity | None = None,
) -> SentActivity:
    """Send or update an activity using the same routing rules as the removed ActivitySender."""
    is_targeted = (
        isinstance(activity, MessageActivityInput)
        and activity.recipient is not None
        and activity.recipient.is_targeted is True
    )

    if is_targeted and ref.conversation.conversation_type == "personal":
        raise ValueError("Targeted messages are not supported in 1:1 (personal) chats.")

    activity.from_ = ref.bot
    activity.conversation = ref.conversation

    if activity.id:
        activity_id = activity.id
        if is_targeted:
            res = await api.conversations.activities_client.update_targeted(
                ref.conversation.id,
                activity_id,
                activity,
                service_url=ref.service_url,
            )
        else:
            res = await api.conversations.activities_client.update(
                ref.conversation.id,
                activity_id,
                activity,
                service_url=ref.service_url,
                agentic_identity=agentic_identity,
            )
        return SentActivity.merge(activity, res)

    if is_targeted:
        res = await api.conversations.activities_client.create_targeted(
            ref.conversation.id,
            activity,
            service_url=ref.service_url,
        )
    else:
        res = await api.conversations.activities_client.create(
            ref.conversation.id,
            activity,
            service_url=ref.service_url,
            agentic_identity=agentic_identity,
        )
    return SentActivity.merge(activity, res)
