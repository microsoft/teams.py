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
    thread_root_id: str | None = None,
) -> SentActivity:
    """Send or update an activity using the same routing rules as the removed ActivitySender."""
    is_targeted = (
        isinstance(activity, MessageActivityInput)
        and activity.recipient is not None
        and activity.recipient.is_targeted is True
    )

    scoped_api = (
        api
        if agentic_identity is None and ref.service_url.rstrip("/") == api.service_url
        else api.clone(service_url=ref.service_url, agentic_identity=agentic_identity)
    )
    if activity.id:
        activity_id = activity.id
        if is_targeted:
            # The recipient of an existing targeted message cannot be edited, so it only selects the
            # targeted endpoint and is dropped from the outbound payload. The caller still gets the
            # recipient back on the returned activity.
            payload = activity.model_copy(update={"recipient": None})
            res = await scoped_api.conversations.update_targeted_activity(ref.conversation.id, activity_id, payload)
            return SentActivity.merge(activity, res.model_copy(update={"activity_params": activity}))

        res = await scoped_api.conversations.update_activity(ref.conversation.id, activity_id, activity)
        return SentActivity.merge(activity, res)

    if is_targeted and thread_root_id is not None:
        res = await scoped_api.conversations.reply_to_targeted_activity(
            ref.conversation.id,
            thread_root_id,
            activity,
        )
    elif is_targeted:
        res = await scoped_api.conversations.create_targeted_activity(ref.conversation.id, activity)
    elif thread_root_id is not None:
        res = await scoped_api.conversations.reply_to_activity(ref.conversation.id, thread_root_id, activity)
    else:
        res = await scoped_api.conversations.create_activity(ref.conversation.id, activity)
    return SentActivity.merge(activity, res)
