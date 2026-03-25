"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List

from ...activities.message.message import MessageActivityInput
from ...models import Account
from ...models.custom_base_model import CustomBaseModel


class BatchUsersParams(CustomBaseModel):
    """Parameters for sending a message to a list of users."""

    tenant_id: str
    "The tenant ID."

    members: List[Account]
    "The users to send the message to. Must contain between 5 and 1000 members."

    activity: MessageActivityInput
    "The message activity to send."


class BatchTenantParams(CustomBaseModel):
    """Parameters for sending a message to all users in a tenant."""

    tenant_id: str
    "The tenant ID."

    activity: MessageActivityInput
    "The message activity to send."


class BatchTeamParams(CustomBaseModel):
    """Parameters for sending a message to all members of a team."""

    tenant_id: str
    "The tenant ID."

    team_id: str
    "The team ID (e.g. '19:...@thread.tacv2')."

    activity: MessageActivityInput
    "The message activity to send."


class BatchChannelsParams(CustomBaseModel):
    """Parameters for sending a message to a list of channels."""

    tenant_id: str
    "The tenant ID."

    members: List[Account]
    "The channels to send the message to."

    activity: MessageActivityInput
    "The message activity to send."
