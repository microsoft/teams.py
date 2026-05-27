"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PendingAsk(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    status: Literal["pending", "answered"] = "pending"
    reply: Optional[str] = None
    event: asyncio.Event = Field(default_factory=asyncio.Event)


class NotifyResult(BaseModel):
    notified: bool
    user_id: str


class AskResult(BaseModel):
    request_id: str


class ReplyResult(BaseModel):
    status: Literal["pending", "answered"]
    reply: Optional[str]


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
