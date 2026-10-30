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
    PlanInfoEntity,
    SentActivity,
)


async def send_or_update_activity(
    api: ApiClient,
    activity: ActivityParams,
    ref: ConversationReference,
    *,
    agentic_identity: AgenticIdentity | None = None,
    reply_chain_id: str | None = None,
) -> SentActivity:
    """Send or update an activity using the same routing rules as the removed ActivitySender.

    `reply_chain_id` is the id of the message at the root of a reply chain (thread).
    When set on a new activity, it is sent as a reply in that thread.
    The thread is in the chat or channel the activity is sent to, identified by `channel_data.chat.id` or
    `channel_data.channel.id`.
    It is ignored when the activity updates an existing message.
    """
    is_targeted = (
        isinstance(activity, MessageActivityInput)
        and activity.recipient is not None
        and activity.recipient.is_targeted is True
    )

    contains_plan = any(isinstance(entity, PlanInfoEntity) for entity in activity.entities or [])

    activity.from_ = ref.bot
    activity.conversation = ref.conversation
    scoped_api = (
        api
        if agentic_identity is None and ref.service_url.rstrip("/") == api.service_url
        else api.clone(service_url=ref.service_url, agentic_identity=agentic_identity)
    )
    if activity.id and not contains_plan:
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

    if reply_chain_id:
        if is_targeted:
            res = await scoped_api.conversations._create_targeted_reply_chain_activity(  # pyright: ignore[reportPrivateUsage]
                ref.conversation.id, reply_chain_id, activity
            )
        else:
            res = await scoped_api.conversations._create_reply_chain_activity(  # pyright: ignore[reportPrivateUsage]
                ref.conversation.id, reply_chain_id, activity
            )
        return SentActivity.merge(activity, res)

    if is_targeted:
        res = await scoped_api.conversations.create_targeted_activity(ref.conversation.id, activity)
    else:
        res = await scoped_api.conversations.create_activity(ref.conversation.id, activity)
    return SentActivity.merge(activity, res)
