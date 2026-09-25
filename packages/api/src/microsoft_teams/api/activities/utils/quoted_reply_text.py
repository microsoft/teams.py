"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ...models import QuotedReplyEntity
from ..protocols import TextActivityProtocol


def format_quoted_reply_placeholder(message_id: str) -> str:
    """Format the Teams text placeholder for a quoted message."""
    return f'<quoted messageId="{message_id}"/>'


def strip_quoted_reply_text(activity: TextActivityProtocol) -> Optional[str]:
    """Remove quoted-message placeholders while preserving quote entities."""
    if not activity.text:
        return None

    quoted_replies = [entity for entity in (activity.entities or []) if isinstance(entity, QuotedReplyEntity)]
    if not quoted_replies:
        return activity.text

    text = activity.text
    changed = False
    for quoted_reply in quoted_replies:
        placeholder = format_quoted_reply_placeholder(quoted_reply.quoted_reply.message_id)
        if placeholder in text:
            text = text.replace(placeholder, "")
            changed = True

    return text.strip() if changed else activity.text
