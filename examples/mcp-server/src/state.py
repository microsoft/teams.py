"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Dict

from models import PendingApproval, PendingAsk

# Maps user_id -> personal conversation_id.
# Populated on first incoming 1:1 message, or on first proactive send.
personal_conversations: Dict[str, str] = {}

# Maps request_id -> PendingAsk (carries its own asyncio.Event for signalling).
pending_asks: Dict[str, PendingAsk] = {}

# Maps approval_id -> PendingApproval (carries its own asyncio.Event for signalling).
pending_approvals: Dict[str, PendingApproval] = {}
