"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# HTML widget utilities for building and validating widget messages.
# Diagnostic: ExperimentalTeamsHtmlWidget

import json
import re
from dataclasses import dataclass
from typing import Any, Optional, cast
from urllib.parse import urlparse

from microsoft_teams.api.activities.message import MessageActivityInput
from microsoft_teams.api.models.html_widget import (
    HtmlWidgetPayload,
    HtmlWidgetSecurityPolicy,
    McpUiUpdateModelContextRequest,
)
from microsoft_teams.common.experimental import experimental
from pydantic import ValidationError

# Default security policy applied when none is specified.
DEFAULT_SECURITY_POLICY = HtmlWidgetSecurityPolicy(
    connect_domains=[],
    resource_domains=["'self'", "data:"],
    frame_domains=[],
    base_uri_domains=[],
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class HtmlWidgetMarkdownOptions:
    """Options for building an HTML widget markdown string."""

    before: Optional[str] = None
    """Text to include before the widget code block."""

    after: Optional[str] = None
    """Text to include after the widget code block."""


@dataclass
class SecurityPolicyWarning:
    """
    A warning produced by validate_security_policy when the widget HTML
    references an external origin not present in the declared security policy.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """

    url: str
    """The URL or origin found in the HTML."""

    source: str
    """The HTML element or API where the reference was found."""

    policy_field: str
    """The security_policy field that should include this origin."""

    message: str
    """A human-readable description of the issue."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_html_widget_payload(payload: HtmlWidgetPayload) -> None:
    """Validates an HTML widget payload, raising if required fields are missing."""
    if not payload.name or not payload.name.strip():
        raise ValueError('HTML widget payload requires a non-empty "name" field.')

    if not payload.html or not payload.html.strip():
        raise ValueError('HTML widget payload requires a non-empty "html" field.')

    domain = (payload.domain or "").strip()
    parsed_domain = urlparse(domain)
    if parsed_domain.scheme != "https" or not parsed_domain.hostname or any(c.isspace() for c in domain):
        raise ValueError('HTML widget payload requires "domain" to be a valid URL starting with "https://".')


# ---------------------------------------------------------------------------
# Building / sending
# ---------------------------------------------------------------------------


@experimental("ExperimentalTeamsHtmlWidget")
def build_html_widget_markdown(
    payload: HtmlWidgetPayload,
    options: Optional[HtmlWidgetMarkdownOptions] = None,
) -> str:
    """
    Wraps an HTML widget payload in the ```html-widget markdown code fence
    format required by Teams to render the widget in a message.
    The widget HTML is sent as authored.
    The widget owns the ui/initialize handshake and the ui/notifications/size-changed reporting.
    Without a size reporter, Teams renders the widget at about 150px tall.
    The optional mcp_url and correlation_id payload fields are serialized only when set.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """
    _validate_html_widget_payload(payload)

    opts = options or HtmlWidgetMarkdownOptions()

    # Apply the default security policy (copied to avoid shared mutation)
    security_policy = payload.security_policy or DEFAULT_SECURITY_POLICY.model_copy(deep=True)
    resolved_payload = payload.model_copy(update={"security_policy": security_policy})
    payload_json = resolved_payload.model_dump(by_alias=True, exclude_none=True)
    json_str = json.dumps(payload_json, separators=(",", ":"))

    parts: list[str] = []
    if opts.before:
        parts.extend([opts.before, ""])

    parts.extend(["```html-widget", json_str, "```"])

    if opts.after:
        parts.extend(["", opts.after])

    return "\n".join(parts)


@experimental("ExperimentalTeamsHtmlWidget")
def build_html_widget_message(
    payload: HtmlWidgetPayload,
    options: Optional[HtmlWidgetMarkdownOptions] = None,
) -> MessageActivityInput:
    """
    Builds a message activity containing an HTML widget, ready to be sent.
    The widget HTML is sent as authored.
    The widget owns the ui/initialize handshake and the ui/notifications/size-changed reporting.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """
    return MessageActivityInput(
        text=build_html_widget_markdown(payload, options),
        text_format="extendedmarkdown",
    )


# ---------------------------------------------------------------------------
# Security validation
# ---------------------------------------------------------------------------


def _extract_origin(url: str) -> Optional[str]:
    """
    Extracts the origin (scheme + host) from a URL string.
    Returns None if the URL is relative, a data URI, or unparseable.
    """
    trimmed = url.strip()
    if not trimmed or trimmed.startswith("data:") or trimmed.startswith("#") or trimmed.startswith("blob:"):
        return None

    # Relative URLs are fine (they resolve to the iframe origin)
    if "://" not in trimmed and not trimmed.startswith("//"):
        return None

    try:
        if trimmed.startswith("//"):
            trimmed = f"https:{trimmed}"
        parsed = urlparse(trimmed)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".lower()
        return None
    except Exception:
        return None


def _is_origin_allowed(origin: str, allowed_domains: list[str]) -> bool:
    """Checks whether an origin is covered by a list of allowed domains/origins."""
    if "*" in allowed_domains:
        return True
    for domain in allowed_domains:
        cleaned = domain.strip("'\"").lower()
        if cleaned == "*":
            return True
        if origin == cleaned:
            return True
        # If the policy entry pins a scheme (e.g. "https://example.com"), the
        # origin must use that same scheme; otherwise fall back to host-only match.
        scheme_match = re.match(r"^(https?)://", cleaned)
        if scheme_match and not origin.startswith(f"{scheme_match.group(1)}://"):
            continue
        domain_host = re.sub(r"^https?://", "", cleaned)
        if origin.endswith(f".{domain_host}"):
            return True
    return False


def _policy_message(source: str, url: str, origin: str, field: str) -> str:
    """Build a human-readable warning message for a policy violation."""
    return f'{source} references "{url}" but origin "{origin}" is not in {field}.'


def _find_tags(html: str, tag_name: str) -> list[str]:
    """
    Find all opening tags by name using string scanning (O(n), no regex backtracking).
    Returns the substring of each tag (from '<tagName' to the next '>').
    """
    tags: list[str] = []
    needle = f"<{tag_name}"
    lower = html.lower()
    pos = 0
    while pos < len(lower):
        start = lower.find(needle, pos)
        if start == -1:
            break
        after_tag = start + len(needle)
        if after_tag < len(lower) and lower[after_tag] not in (" ", "\t", "\n", "\r", ">", "/"):
            pos = after_tag
            continue
        end = html.find(">", start)
        if end == -1:
            break
        tags.append(html[start : end + 1])
        pos = end + 1
    return tags


@experimental("ExperimentalTeamsHtmlWidget")
def validate_security_policy(html: str, policy: HtmlWidgetSecurityPolicy) -> list[SecurityPolicyWarning]:
    """
    Validates that external references in widget HTML are covered by the
    declared security policy. Returns a list of warnings for any references
    to origins not present in the appropriate policy field.

    This is a static analysis tool - it cannot catch dynamically constructed URLs.
    Dynamically built URLs are only visible at runtime, in the widget's CSP violation reports.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """
    warnings: list[SecurityPolicyWarning] = []

    # resourceDomains: <script src>, <link href>, <img src>, <source src>,
    # <audio src>, <video src>, CSS url(), @import
    tag_attr_checks = [
        ("script", re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE), "<script src>"),
        ("link", re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE), "<link href>"),
        ("img", re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE), "<img src>"),
        ("source", re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE), "<source src>"),
        ("audio", re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE), "<audio src>"),
        ("video", re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE), "<video src>"),
    ]

    for tag_name, attr_regex, source in tag_attr_checks:
        for tag_str in _find_tags(html, tag_name):
            attr_match = attr_regex.search(tag_str)
            if attr_match:
                origin = _extract_origin(attr_match.group(1))
                if origin and not _is_origin_allowed(origin, policy.resource_domains or []):
                    warnings.append(
                        SecurityPolicyWarning(
                            url=attr_match.group(1),
                            source=source,
                            policy_field="resourceDomains",
                            message=_policy_message(source, attr_match.group(1), origin, "resourceDomains"),
                        )
                    )

    # CSS url() and @import
    css_patterns = [
        (re.compile(r'url\(\s*["\']([^"\')\s]+)["\']\s*\)', re.IGNORECASE), "CSS url()"),
        (re.compile(r'@import\s+["\']([^"\']+)["\']', re.IGNORECASE), "CSS @import"),
    ]

    for regex, source in css_patterns:
        for match in regex.finditer(html):
            origin = _extract_origin(match.group(1))
            if origin and not _is_origin_allowed(origin, policy.resource_domains or []):
                warnings.append(
                    SecurityPolicyWarning(
                        url=match.group(1),
                        source=source,
                        policy_field="resourceDomains",
                        message=_policy_message(source, match.group(1), origin, "resourceDomains"),
                    )
                )

    # connectDomains: fetch(), XMLHttpRequest.open(), new WebSocket(), new EventSource()
    connect_patterns = [
        (re.compile(r'fetch\(\s*["\']([^"\']+)["\']', re.IGNORECASE), "fetch()"),
        (
            re.compile(r'\.open\(\s*["\'][A-Za-z]+["\']\s*,\s*["\']([^"\']+)["\']', re.IGNORECASE),
            "XMLHttpRequest.open()",
        ),
        (re.compile(r'new\s+WebSocket\(\s*["\']([^"\']+)["\']', re.IGNORECASE), "new WebSocket()"),
        (re.compile(r'new\s+EventSource\(\s*["\']([^"\']+)["\']', re.IGNORECASE), "new EventSource()"),
    ]

    for regex, source in connect_patterns:
        for match in regex.finditer(html):
            origin = _extract_origin(match.group(1))
            if origin and not _is_origin_allowed(origin, policy.connect_domains or []):
                warnings.append(
                    SecurityPolicyWarning(
                        url=match.group(1),
                        source=source,
                        policy_field="connectDomains",
                        message=_policy_message(source, match.group(1), origin, "connectDomains"),
                    )
                )

    # frameDomains: <iframe src>
    for tag_str in _find_tags(html, "iframe"):
        attr_match = re.search(r'src=["\']([^"\']+)["\']', tag_str, re.IGNORECASE)
        if attr_match:
            origin = _extract_origin(attr_match.group(1))
            if origin and not _is_origin_allowed(origin, policy.frame_domains or []):
                warnings.append(
                    SecurityPolicyWarning(
                        url=attr_match.group(1),
                        source="<iframe src>",
                        policy_field="frameDomains",
                        message=_policy_message("<iframe src>", attr_match.group(1), origin, "frameDomains"),
                    )
                )

    # connectDomains: <form action>
    for tag_str in _find_tags(html, "form"):
        attr_match = re.search(r'action=["\']([^"\']+)["\']', tag_str, re.IGNORECASE)
        if attr_match:
            origin = _extract_origin(attr_match.group(1))
            if origin and not _is_origin_allowed(origin, policy.connect_domains or []):
                warnings.append(
                    SecurityPolicyWarning(
                        url=attr_match.group(1),
                        source="<form action>",
                        policy_field="connectDomains",
                        message=_policy_message("<form action>", attr_match.group(1), origin, "connectDomains"),
                    )
                )

    # baseUriDomains: <base href>
    for tag_str in _find_tags(html, "base"):
        attr_match = re.search(r'href=["\']([^"\']+)["\']', tag_str, re.IGNORECASE)
        if attr_match:
            origin = _extract_origin(attr_match.group(1))
            if origin and not _is_origin_allowed(origin, policy.base_uri_domains or []):
                warnings.append(
                    SecurityPolicyWarning(
                        url=attr_match.group(1),
                        source="<base href>",
                        policy_field="baseUriDomains",
                        message=_policy_message("<base href>", attr_match.group(1), origin, "baseUriDomains"),
                    )
                )

    return warnings


@experimental("ExperimentalTeamsHtmlWidget")
def try_get_widget_model_context(activity: Any) -> Optional[McpUiUpdateModelContextRequest]:
    """Attempt to extract an MCP UI update-model-context request from a message activity's value.

    A widget can request that content be added to the model context by reusing the messageBack
    mechanism (like Action.Submit for adaptive cards).
    Such a request arrives as a normal message activity whose value carries the
    McpUiUpdateModelContextRequest payload.
    This is fire-and-forget: the bot does not respond.

    This helper is tolerant of two wire shapes:
      1. The raw request object ({"method": "ui/update-model-context", "params": ...}).
      2. An envelope of the form {"type": "widgetModelContext", "data": <request>}.

    Args:
        activity: A message activity (or any object with a value attribute).

    Returns:
        The parsed request, or None if value is not a valid update-model-context request.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """
    value = cast("dict[str, Any] | None", getattr(activity, "value", None))
    if not isinstance(value, dict):
        return None

    # Unwrap the {"type": "widgetModelContext", "data": ...} envelope if present.
    candidate: dict[str, Any] = value
    if value.get("type") == "widgetModelContext" and isinstance(value.get("data"), dict):
        candidate = cast("dict[str, Any]", value["data"])

    if candidate.get("method") != "ui/update-model-context":
        return None

    if not isinstance(candidate.get("params"), dict):
        return None

    try:
        return McpUiUpdateModelContextRequest.model_validate(candidate)
    except ValidationError:
        return None
