"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel


@experimental("ExperimentalTeamsHtmlWidget")
class HtmlWidgetSecurityPolicy(CustomBaseModel):
    """
    The security policy for an HTML widget, controlling allowed origins
    for network requests, static resources, nested iframes, and base URIs.

    @experimental This API is in preview and may change in the future.
    """

    connect_domains: Optional[list[str]] = None
    """Allowed origins for network requests."""

    resource_domains: Optional[list[str]] = None
    """Allowed origins for static resources."""

    frame_domains: Optional[list[str]] = None
    """Allowed origins for nested iframes."""

    base_uri_domains: Optional[list[str]] = None
    """Allowed base URIs for the document."""


@experimental("ExperimentalTeamsHtmlWidget")
class HtmlWidgetPermissions(CustomBaseModel):

    camera: Optional[Any] = None
    """Request camera access."""

    microphone: Optional[Any] = None
    """Request microphone access."""

    geolocation: Optional[Any] = None
    """Request geolocation access."""

    clipboard_write: Optional[Any] = None
    """Request clipboard write access."""


@experimental("ExperimentalTeamsHtmlWidget")
class HtmlWidgetPayload(CustomBaseModel):

    type: Literal["widget/mcp-ui"] = "widget/mcp-ui"
    """The widget type identifier. Currently only "widget/mcp-ui" is supported."""

    name: str
    """The display name of the MCP app."""

    description: Optional[str] = None
    """A description of the MCP app."""

    html: str
    """The HTML content that makes up the widget."""

    domain: str
    """The domain associated with the widget. Must start with 'https://'."""

    security_policy: Optional[HtmlWidgetSecurityPolicy] = None
    """Optional security policy controlling allowed origins."""

    tool_input: Optional[Any] = None
    """Optional data that was passed as input to the tool that produced this widget."""

    tool_output: Optional[Any] = None
    """Optional data that the tool produced alongside this widget."""

    permissions: Optional[HtmlWidgetPermissions] = None
    """Optional permissions the widget requests from the host."""
