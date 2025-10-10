"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClientContext:
    """
    Runtime information about the client and session in Microsoft Teams.
    """

    app_session_id: str
    """Unique ID for the current session for use in correlating telemetry data.
    A session corresponds to the lifecycle of an app.
    A new session begins upon the creation of a webview (on Teams mobile) or iframe (in Teams desktop) hosting the app,
    and ends when it is destroyed."""

    tenant_id: str
    """The Microsoft Entra tenant ID of the current user, extracted from request auth token."""

    user_id: str
    """The Microsoft Entra object ID of the current user, extracted from the request auth token."""

    user_name: str
    """The name of the current user, extracted from the request auth token."""

    page_id: str
    """The developer-defined unique ID for the page this content points to."""

    auth_token: str
    """The MSAL Entra token."""

    app_id: Optional[str] = None
    """This ID is the unique identifier assigned to the app after deployment and is critical for ensuring the correct
    app instance is recognized across hosts."""

    team_id: Optional[str] = None
    """The Microsoft Teams ID for the team with which the content is associated."""

    message_id: Optional[str] = None
    """The ID of the parent message from which this task module was launched.
    This is only available in task modules launched from bot cards."""

    channel_id: Optional[str] = None
    """The Microsoft Teams ID for the channel with which the content is associated."""

    chat_id: Optional[str] = None
    """The Microsoft Teams ID for the chat with which the content is associated."""

    meeting_id: Optional[str] = None
    """Meeting ID used by tab when running in meeting context."""

    sub_page_id: Optional[str] = None
    """The developer-defined unique ID for the sub-page this content points to.
    This field should be used to restore to a specific state within a page,
    such as scrolling to or activating a specific piece of content."""

    _resolved_conversation_id: Optional[str] = None
    """The Microsoft Teams ID for the conversation with which the content is associated."""

    @property
    def conversation_id(self) -> Optional[str]:
        """The Microsoft Teams ID for the conversation with which the content is associated."""
        return self._resolved_conversation_id
