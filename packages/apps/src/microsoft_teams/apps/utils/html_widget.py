"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

HTML widget utilities for building and validating widget messages.

Diagnostic: ExperimentalTeamsHtmlWidget
"""

import json
import re
from dataclasses import dataclass, replace
from typing import Optional
from urllib.parse import urlparse

from microsoft_teams.api.activities.message import MessageActivityInput
from microsoft_teams.api.models.html_widget import HtmlWidgetPayload, HtmlWidgetSecurityPolicy
from microsoft_teams.common.experimental import experimental

# The MCP Apps protocol version used for the widget init handshake.
MCP_PROTOCOL_VERSION = "2026-01-26"

# Explicit mapping of notification names to their window callback names.
# Only notifications in this map will have hooks injected.
#
# Supported in the Teams app bridge: tool-result, tool-input
# Not supported in the Teams app bridge: tool-input-partial, tool-cancelled
# Not yet available in Teams: host-context-changed, resource-teardown
NOTIFICATION_CALLBACKS: dict[str, str] = {
    "tool-result": "onToolResult",
    "tool-input": "onToolInput",
    "tool-input-partial": "onToolInputPartial",
    "tool-cancelled": "onToolCancelled",
    "host-context-changed": "onHostContextChanged",
    "resource-teardown": "onResourceTeardown",
}

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
class InjectWidgetProtocolOptions:
    """Options for injecting the MCP Apps protocol into widget HTML."""

    name: Optional[str] = None
    """The widget app name sent during ui/initialize. Defaults to 'widget'."""

    version: Optional[str] = None
    """The widget app version sent during ui/initialize. Defaults to '1.0.0'."""

    available_display_modes: Optional[list[str]] = None
    """Display modes this widget supports (e.g. ['inline', 'fullscreen'])."""

    notifications: Optional[list[str]] = None
    """Host notifications to listen for (e.g. ['tool-result', 'tool-input'])."""

    debug_csp_violations: bool = False
    """When true, injects a CSP violation listener for dev-time debugging."""


@dataclass
class HtmlWidgetMarkdownOptions:
    """Options for building an HTML widget markdown string."""

    before: Optional[str] = None
    """Text to include before the widget code block."""

    after: Optional[str] = None
    """Text to include after the widget code block."""

    protocol_options: Optional[InjectWidgetProtocolOptions] = None
    """Options forwarded to inject_widget_protocol."""


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

    if not payload.domain or not payload.domain.strip() or not payload.domain.startswith("https://"):
        raise ValueError('HTML widget payload requires "domain" to be a valid URL starting with "https://".')


# ---------------------------------------------------------------------------
# Protocol injection
# ---------------------------------------------------------------------------


@experimental("ExperimentalTeamsHtmlWidget")
def inject_widget_protocol(html: str, options: Optional[InjectWidgetProtocolOptions] = None) -> str:
    """
    Injects the MCP Apps protocol script into widget HTML.

    This sets up:
    - The ui/initialize handshake (required for rendering)
    - Size reporting via ui/notifications/size-changed
    - Optional notification hooks (opt-in via notifications option)

    If the HTML already contains the protocol (detected by 'ui/initialize'), it is returned unchanged.

    Diagnostic: ExperimentalTeamsHtmlWidget
    """
    if "ui/initialize" in html:
        return html

    opts = options or InjectWidgetProtocolOptions()
    name = (opts.name or "widget").replace("\\", "\\\\").replace("'", "\\'")
    version = (opts.version or "1.0.0").replace("\\", "\\\\").replace("'", "\\'")

    caps_json = "{}"
    if opts.available_display_modes:
        caps_json = f"{{availableDisplayModes:{json.dumps(opts.available_display_modes)}}}"

    # Build notification hook lines
    notifications = opts.notifications or []
    hook_lines = ""
    for n in notifications:
        if n in NOTIFICATION_CALLBACKS:
            method = f"ui/notifications/{n}"
            cb = NOTIFICATION_CALLBACKS[n]
            hook_lines += f"if(d.method==='{method}'&&window.{cb}){{window.{cb}(d.params);}}"

    # CSP violation listener (dev-only, opt-in)
    csp_debug = ""
    if opts.debug_csp_violations:
        csp_debug = (
            "document.addEventListener('securitypolicyviolation',function(e){"
            "console.warn('[widget CSP violation]',{"
            "blockedURI:e.blockedURI,"
            "violatedDirective:e.violatedDirective,"
            "originalPolicy:e.originalPolicy"
            "});});"
        )

    # Script template parts (long JS strings, cannot break mid-expression)
    notify_size = (  # noqa: E501
        "function notifySize(){window.parent.postMessage("
        "{jsonrpc:'2.0',method:'ui/notifications/size-changed',"
        "params:{height:document.body.scrollHeight}},'*');}"
    )
    on_init = (
        "if(d.id===id&&d.result){window.parent.postMessage("
        "{jsonrpc:'2.0',method:'ui/notifications/initialized'},'*');"
        "setTimeout(notifySize,100);}"
    )
    post_init = (
        "window.parent.postMessage({jsonrpc:'2.0',id:id,"
        f"method:'ui/initialize',params:{{protocolVersion:'{MCP_PROTOCOL_VERSION}',"
        f"appInfo:{{name:'{name}',version:'{version}'}},"
        f"appCapabilities:{caps_json}}}}},'*');"
    )

    script = (
        "<script>(function(){"
        + csp_debug
        + "var id='init-'+Math.random().toString(36).slice(2);"
        + notify_size
        + "window.addEventListener('message',function(e){"
        + "var d=e.data;if(!d||d.jsonrpc!=='2.0')return;"
        + on_init
        + hook_lines
        + "});"
        + post_init
        + "document.addEventListener('DOMContentLoaded',notifySize);"
        + "})()</script>"
    )

    # Inject before </body> if present, otherwise append
    if "</body>" in html:
        return html.replace("</body>", script + "</body>")

    return html + script


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

    Diagnostic: ExperimentalTeamsHtmlWidget
    """
    _validate_html_widget_payload(payload)

    opts = options or HtmlWidgetMarkdownOptions()

    # Build protocol options from markdown options (copy to avoid mutating caller's instance)
    base_proto = opts.protocol_options or InjectWidgetProtocolOptions()
    proto_opts = replace(base_proto, name=payload.name)

    # Inject protocol and apply default security policy (copy default to avoid shared mutation)
    injected_html = inject_widget_protocol(payload.html, proto_opts)
    security_policy = payload.security_policy or DEFAULT_SECURITY_POLICY.model_copy(deep=True)

    # Build the serialized payload
    injected_payload = payload.model_copy(update={"html": injected_html, "security_policy": security_policy})
    payload_json = injected_payload.model_dump(by_alias=True, exclude_none=True)
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
            return f"{parsed.scheme}://{parsed.netloc}"
        return None
    except Exception:
        return None


def _is_origin_allowed(origin: str, allowed_domains: list[str]) -> bool:
    """Checks whether an origin is covered by a list of allowed domains/origins."""
    if "*" in allowed_domains:
        return True
    for domain in allowed_domains:
        cleaned = domain.strip("'\"")
        if cleaned == "*":
            return True
        if origin == cleaned:
            return True
        # Check subdomain match
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
    Use the debug_csp_violations option on inject_widget_protocol for runtime detection.

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

    return warnings
