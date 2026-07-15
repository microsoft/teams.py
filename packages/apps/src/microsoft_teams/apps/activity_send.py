"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import (
    AGENTIC_IDENTITY_PRESERVE,
    ActivityParams,
    AgenticIdentityScope,
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
    agentic_identity: AgenticIdentityScope = AGENTIC_IDENTITY_PRESERVE,
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
    scoped_api = api.clone(service_url=ref.service_url, agentic_identity=agentic_identity)
    if activity.id:
        activity_id = activity.id
        if is_targeted:
            res = await scoped_api.conversations.update_targeted_activity(ref.conversation.id, activity_id, activity)
        else:
            res = await scoped_api.conversations.update_activity(ref.conversation.id, activity_id, activity)
        return SentActivity.merge(activity, res)

    if is_targeted:
        res = await scoped_api.conversations.create_targeted_activity(ref.conversation.id, activity)
    else:
        res = await scoped_api.conversations.create_activity(ref.conversation.id, activity)
    return SentActivity.merge(activity, res)
