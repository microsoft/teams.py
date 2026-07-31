"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .agent_lifecycle import (
    AgenticUserDeletedActivity,
    AgenticUserDeletedValue,
    AgenticUserDisabledActivity,
    AgenticUserDisabledValue,
    AgenticUserEnabledActivity,
    AgenticUserEnabledValue,
    AgenticUserIdentityCreatedActivity,
    AgenticUserIdentityCreatedValue,
    AgenticUserIdentityUpdatedActivity,
    AgenticUserIdentityUpdatedValue,
    AgenticUserManagerUpdatedActivity,
    AgenticUserManagerUpdatedValue,
    AgenticUserUndeletedActivity,
    AgenticUserUndeletedValue,
    AgenticUserWorkloadOnboardingUpdatedActivity,
    AgenticUserWorkloadOnboardingUpdatedValue,
    AgentLifecycleEventActivity,
    AgentLifecycleEventActivityBase,
    AgentLifecycleManager,
    AgentLifecycleManagerRef,
    AgentLifecycleUpdatedProperty,
    AgentLifecycleValueBase,
)
from .meeting_end import MeetingEndEventActivity
from .meeting_participant import MeetingParticipantEventActivity
from .meeting_participant_join import MeetingParticipantJoinEventActivity
from .meeting_participant_leave import MeetingParticipantLeaveEventActivity
from .meeting_start import MeetingStartEventActivity
from .read_reciept import ReadReceiptEventActivity

EventActivity = Annotated[
    Union[
        ReadReceiptEventActivity,
        MeetingStartEventActivity,
        MeetingEndEventActivity,
        MeetingParticipantJoinEventActivity,
        MeetingParticipantLeaveEventActivity,
        AgentLifecycleEventActivity,
    ],
    Field(discriminator="name"),
]

__all__ = [
    "MeetingEndEventActivity",
    "MeetingStartEventActivity",
    "MeetingParticipantEventActivity",
    "MeetingParticipantJoinEventActivity",
    "MeetingParticipantLeaveEventActivity",
    "ReadReceiptEventActivity",
    "EventActivity",
    "AgentLifecycleEventActivity",
    "AgentLifecycleEventActivityBase",
    "AgenticUserIdentityCreatedActivity",
    "AgenticUserIdentityUpdatedActivity",
    "AgenticUserManagerUpdatedActivity",
    "AgenticUserEnabledActivity",
    "AgenticUserDisabledActivity",
    "AgenticUserDeletedActivity",
    "AgenticUserUndeletedActivity",
    "AgenticUserWorkloadOnboardingUpdatedActivity",
    "AgentLifecycleManager",
    "AgentLifecycleManagerRef",
    "AgentLifecycleUpdatedProperty",
    "AgentLifecycleValueBase",
    "AgenticUserIdentityCreatedValue",
    "AgenticUserIdentityUpdatedValue",
    "AgenticUserManagerUpdatedValue",
    "AgenticUserEnabledValue",
    "AgenticUserDisabledValue",
    "AgenticUserDeletedValue",
    "AgenticUserUndeletedValue",
    "AgenticUserWorkloadOnboardingUpdatedValue",
]
