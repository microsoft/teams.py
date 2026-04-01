"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, List, Optional

from ..custom_base_model import CustomBaseModel


class MeetingNotificationSurface(CustomBaseModel):
    """
    A surface target for a meeting notification.
    """

    surface: str
    "The surface type. E.g. 'meetingStage', 'meetingTabIcon', 'meetingCopilotPane'."

    content_type: Optional[str] = None
    "The content type for surfaces that carry content. E.g. 'task'."

    content: Optional[Dict[str, Any]] = None
    "The content payload for the surface."

    tab_entity_id: Optional[str] = None
    "The tab entity ID, required for 'meetingTabIcon' surfaces."


class MeetingNotificationValue(CustomBaseModel):
    """
    The value of a targeted meeting notification.
    """

    recipients: List[str]
    "AAD object IDs of the meeting participants to notify."

    surfaces: List[MeetingNotificationSurface]
    "The surfaces to send the notification to."


class MeetingNotificationParams(CustomBaseModel):
    """
    Parameters for sending a meeting notification.
    """

    type: str = "targetedMeetingNotification"
    "The notification type."

    value: MeetingNotificationValue
    "The notification value containing recipients and surfaces."


class MeetingNotificationRecipientFailure(CustomBaseModel):
    """
    Information about a recipient that failed to receive a meeting notification.
    """

    recipient_mri: Optional[str] = None
    "The MRI of the recipient."

    error_code: Optional[str] = None
    "The error code."

    failure_reason: Optional[str] = None
    "The reason for the failure."


class MeetingNotificationResponse(CustomBaseModel):
    """
    Response from a meeting notification request when some or all recipients failed (HTTP 207).
    None is returned when all notifications were sent successfully (HTTP 202).
    """

    recipients_failure_info: Optional[List[MeetingNotificationRecipientFailure]] = None
    "Information about recipients that failed to receive the notification."
