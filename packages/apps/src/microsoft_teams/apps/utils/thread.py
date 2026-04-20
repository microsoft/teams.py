"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""


def to_threaded_conversation_id(conversation_id: str, message_id: str) -> str:
    """Construct a threaded conversation ID by appending `;messageid={message_id}`
    to the conversation ID. This is the format APX uses to route messages
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

    # Strip any existing ;messageid= suffix (mirrors APX's NormalizeConversationId)
    base_id = conversation_id.split(";")[0]
    return f"{base_id};messageid={message_id}"
