"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from typing import Dict, Literal

from models import PendingAsk

# Maps user_id -> personal conversation_id.
# Populated on first incoming 1:1 message, or on first proactive send.
personal_conversations: Dict[str, str] = {}

# Maps request_id -> PendingAsk.
pending_asks: Dict[str, PendingAsk] = {}

# Maps user_id -> request_id for their current pending ask.
# Cleared once the user replies.
user_pending_ask: Dict[str, str] = {}

# Maps approval_id -> approval status.
approvals: Dict[str, Literal["pending", "approved", "rejected"]] = {}

# Maps request_id -> Future[PendingAsk]. Signalled when the user replies.
# Lets wait_for_reply return immediately after the answer lands.
reply_waiters: Dict[str, "asyncio.Future[PendingAsk]"] = {}

# Maps approval_id -> Future[str]. Signalled when the user clicks Approve/Reject.
# Lets wait_for_approval return immediately after the decision lands.
approval_waiters: Dict[str, "asyncio.Future[str]"] = {}
