"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import re

from typing_extensions import deprecated

_LEGACY_THREADED_CONVERSATION_ID = re.compile(r"^(?P<conversation_id>.+);messageid=(?P<message_id>\d+)$")


@deprecated(
    "to_threaded_conversation_id is deprecated. Use App.reply(conversation_id, message_id, activity) "
    "to place a message in a thread."
)
def to_threaded_conversation_id(conversation_id: str, message_id: str) -> str:
    """Construct a threaded conversation ID by appending `;messageid={message_id}`
    to the conversation ID. This is the format the service uses to route messages
    to a specific thread.

    Args:
        conversation_id: The conversation to thread into (e.g. `19:abc@thread.skype`)
        message_id: The thread root message ID (must be a non-zero numeric string)

    Returns:
        The threaded conversation ID (e.g. `19:abc@thread.skype;messageid=123`)
    """
    if not conversation_id:
        raise ValueError("conversation_id must be a non-empty string")

    if not message_id or not message_id.isdigit() or message_id == "0":
        raise ValueError(f'Invalid message_id "{message_id}": must be a non-zero numeric value')

    # Strip any existing ;messageid= suffix (mirrors the service's conversation-ID normalization)
    base_id = conversation_id.split(";")[0]
    return f"{base_id};messageid={message_id}"


def parse_threaded_conversation_id(conversation_id: str) -> tuple[str, str | None]:
    """Split a valid legacy threaded conversation ID into its base ID and thread root."""
    match = _LEGACY_THREADED_CONVERSATION_ID.fullmatch(conversation_id)
    if match is None or match.group("message_id") == "0":
        return conversation_id, None
    return match.group("conversation_id"), match.group("message_id")
