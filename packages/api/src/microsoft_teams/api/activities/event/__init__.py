"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .agent_lifecycle import (
    AgenticIdentityCreatedActivity,
    AgenticIdentityCreatedValue,
    AgenticIdentityDeletedActivity,
    AgenticIdentityDeletedValue,
    AgenticIdentityDisabledActivity,
    AgenticIdentityDisabledValue,
    AgenticIdentityEnabledActivity,
    AgenticIdentityEnabledValue,
    AgenticIdentityManagerUpdatedActivity,
    AgenticIdentityManagerUpdatedValue,
    AgenticIdentityUndeletedActivity,
    AgenticIdentityUndeletedValue,
    AgenticIdentityUpdatedActivity,
    AgenticIdentityUpdatedValue,
    AgenticIdentityWorkloadOnboardingUpdatedActivity,
    AgenticIdentityWorkloadOnboardingUpdatedValue,
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
    "AgenticIdentityCreatedActivity",
    "AgenticIdentityUpdatedActivity",
    "AgenticIdentityManagerUpdatedActivity",
    "AgenticIdentityEnabledActivity",
    "AgenticIdentityDisabledActivity",
    "AgenticIdentityDeletedActivity",
    "AgenticIdentityUndeletedActivity",
    "AgenticIdentityWorkloadOnboardingUpdatedActivity",
    "AgentLifecycleManager",
    "AgentLifecycleManagerRef",
    "AgentLifecycleUpdatedProperty",
    "AgentLifecycleValueBase",
    "AgenticIdentityCreatedValue",
    "AgenticIdentityUpdatedValue",
    "AgenticIdentityManagerUpdatedValue",
    "AgenticIdentityEnabledValue",
    "AgenticIdentityDisabledValue",
    "AgenticIdentityDeletedValue",
    "AgenticIdentityUndeletedValue",
    "AgenticIdentityWorkloadOnboardingUpdatedValue",
]
