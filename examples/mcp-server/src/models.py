"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel


@dataclass
class PendingAsk:
    """In-process state for a pending ask. Holds a live asyncio.Event, never serialized."""

    user_id: str
    status: Literal["pending", "answered"] = "pending"
    reply: Optional[str] = None
    event: asyncio.Event = field(default_factory=asyncio.Event)


class NotifyResult(BaseModel):
    notified: bool
    user_id: str


class AskResult(BaseModel):
    request_id: str


class ReplyResult(BaseModel):
    status: Literal["pending", "answered"]
    reply: Optional[str]


@dataclass
class PendingApproval:
    """In-process state for a pending approval. Holds a live asyncio.Event, never serialized."""

    user_id: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    event: asyncio.Event = field(default_factory=asyncio.Event)


class ApprovalRequestResult(BaseModel):
    approval_id: str


class ApprovalResult(BaseModel):
    approval_id: str
    status: Literal["pending", "approved", "rejected"]


class UserMatch(BaseModel):
    id: str
    display_name: Optional[str]
    user_principal_name: Optional[str]


class FindUserResult(BaseModel):
    matches: list[UserMatch]
