"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for HTML widget utilities.
"""

import json
import warnings
from typing import Any

import pytest
from microsoft_teams.api.models.html_widget import (
    HtmlWidgetPayload,
    HtmlWidgetPermissions,
    HtmlWidgetSecurityPolicy,
)
from microsoft_teams.apps.utils.html_widget import (
    HtmlWidgetMarkdownOptions,
    InjectWidgetProtocolOptions,
    build_html_widget_markdown,
    build_html_widget_message,
    inject_widget_protocol,
    validate_security_policy,
)
from microsoft_teams.common.experimental import ExperimentalWarning

# Suppress ExperimentalWarning in all widget tests
warnings.filterwarnings("ignore", category=ExperimentalWarning)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_PAYLOAD = HtmlWidgetPayload(
    name="Test Widget",
    html="<div>Hello</div>",
    domain="https://example.com",
)

FULL_PAYLOAD = HtmlWidgetPayload(
    name="Weather Widget",
    description="Current weather conditions",
    html='<div class="weather">72F</div>',
    domain="https://weather.example.com",
    security_policy=HtmlWidgetSecurityPolicy(
        connect_domains=["https://api.example.com"],
        resource_domains=["'self'", "data:"],
        frame_domains=[],
        base_uri_domains=[],
    ),
    tool_input={"location": "Seattle, WA"},
    tool_output={
        "content": [{"type": "text", "text": "Seattle: 72F"}],
        "structuredContent": {"tempF": 72},
        "isError": False,
    },
    permissions=HtmlWidgetPermissions(clipboard_write={}),
)

EMPTY_POLICY = HtmlWidgetSecurityPolicy(
    connect_domains=[],
    resource_domains=[],
    frame_domains=[],
    base_uri_domains=[],
)


def _parse_widget_json(markdown: str) -> dict[str, Any]:
    """Extract and parse JSON from widget markdown."""
    lines = markdown.split("\n")
    # Find content between ```html-widget and ```
    start = lines.index("```html-widget") + 1
    end = len(lines) - 1 - lines[::-1].index("```")
    json_str = "\n".join(lines[start:end])
    return json.loads(json_str)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# build_html_widget_markdown
# ---------------------------------------------------------------------------


class TestBuildHtmlWidgetMarkdown:
    def test_wraps_payload_in_code_fence(self):
        result = build_html_widget_markdown(MINIMAL_PAYLOAD)
        assert result.startswith("```html-widget\n")
        assert result.endswith("\n```")

    def test_auto_injects_widget_protocol(self):
        result = build_html_widget_markdown(MINIMAL_PAYLOAD)
        parsed = _parse_widget_json(result)
        assert "ui/initialize" in parsed["html"]
        assert "<div>Hello</div>" in parsed["html"]

    def test_no_double_inject_if_already_has_protocol(self):
        html_with_init = "<div>Hello</div><script>ui/initialize</script>"
        payload = MINIMAL_PAYLOAD.model_copy(update={"html": html_with_init})
        result = build_html_widget_markdown(payload)
        parsed = _parse_widget_json(result)
        assert parsed["html"] == html_with_init

    def test_uses_payload_name_as_protocol_app_name(self):
        result = build_html_widget_markdown(MINIMAL_PAYLOAD)
        parsed = _parse_widget_json(result)
        assert "name:'Test Widget'" in parsed["html"]

    def test_includes_text_before_widget(self):
        opts = HtmlWidgetMarkdownOptions(before="Check this out:")
        result = build_html_widget_markdown(MINIMAL_PAYLOAD, opts)
        assert result.startswith("Check this out:\n\n```html-widget\n")

    def test_includes_text_after_widget(self):
        opts = HtmlWidgetMarkdownOptions(after="Pretty cool, right?")
        result = build_html_widget_markdown(MINIMAL_PAYLOAD, opts)
        assert result.endswith("\n```\n\nPretty cool, right?")

    def test_includes_text_before_and_after(self):
        opts = HtmlWidgetMarkdownOptions(before="Before", after="After")
        result = build_html_widget_markdown(MINIMAL_PAYLOAD, opts)
        assert result.startswith("Before\n\n```html-widget\n")
        assert result.endswith("\n```\n\nAfter")

    def test_forwards_protocol_options(self):
        opts = HtmlWidgetMarkdownOptions(protocol_options=InjectWidgetProtocolOptions(notifications=["tool-result"]))
        result = build_html_widget_markdown(MINIMAL_PAYLOAD, opts)
        parsed = _parse_widget_json(result)
        assert "ui/notifications/tool-result" in parsed["html"]
        assert "window.onToolResult" in parsed["html"]

    def test_forwards_debug_csp_violations(self):
        opts = HtmlWidgetMarkdownOptions(protocol_options=InjectWidgetProtocolOptions(debug_csp_violations=True))
        result = build_html_widget_markdown(MINIMAL_PAYLOAD, opts)
        parsed = _parse_widget_json(result)
        assert "securitypolicyviolation" in parsed["html"]

    def test_uses_payload_name_even_with_protocol_options(self):
        opts = HtmlWidgetMarkdownOptions(protocol_options=InjectWidgetProtocolOptions(version="2.0.0"))
        result = build_html_widget_markdown(MINIMAL_PAYLOAD, opts)
        parsed = _parse_widget_json(result)
        assert "name:'Test Widget'" in parsed["html"]
        assert "version:'2.0.0'" in parsed["html"]

    def test_serializes_full_payload_with_all_fields(self):
        result = build_html_widget_markdown(FULL_PAYLOAD)
        parsed = _parse_widget_json(result)
        assert parsed["type"] == "widget/mcp-ui"
        assert parsed["name"] == "Weather Widget"
        assert parsed["description"] == "Current weather conditions"
        assert '<div class="weather">72F</div>' in parsed["html"]
        assert "ui/initialize" in parsed["html"]
        assert parsed["domain"] == "https://weather.example.com"
        assert parsed["securityPolicy"]["connectDomains"] == ["https://api.example.com"]
        assert parsed["toolInput"] == {"location": "Seattle, WA"}
        assert parsed["permissions"] == {"clipboardWrite": {}}

    def test_does_not_overwrite_user_security_policy(self):
        custom_policy = HtmlWidgetSecurityPolicy(
            connect_domains=["https://api.custom.com"],
            resource_domains=["https://cdn.custom.com"],
            frame_domains=["https://embed.custom.com"],
            base_uri_domains=[],
        )
        payload = MINIMAL_PAYLOAD.model_copy(update={"security_policy": custom_policy})
        result = build_html_widget_markdown(payload)
        parsed = _parse_widget_json(result)
        assert parsed["securityPolicy"]["connectDomains"] == ["https://api.custom.com"]
        assert parsed["securityPolicy"]["resourceDomains"] == ["https://cdn.custom.com"]
        assert parsed["securityPolicy"]["frameDomains"] == ["https://embed.custom.com"]

    def test_handles_html_with_backticks(self):
        payload = MINIMAL_PAYLOAD.model_copy(update={"html": "<code>```some code```</code>"})
        result = build_html_widget_markdown(payload)
        assert result.startswith("```html-widget\n")
        assert result.endswith("\n```")
        parsed = _parse_widget_json(result)
        assert "<code>```some code```</code>" in parsed["html"]

    def test_handles_html_with_newlines_and_special_chars(self):
        payload = MINIMAL_PAYLOAD.model_copy(update={"html": "<div>\n  <p>\"Hello\" & 'world'</p>\n</div>"})
        result = build_html_widget_markdown(payload)
        # JSON is on a single line (compact), just parse the first line after fence
        json_line = result.split("\n")[1]
        parsed = json.loads(json_line)
        assert "<div>\n  <p>\"Hello\" & 'world'</p>\n</div>" in parsed["html"]

    def test_empty_options_no_extra_lines(self):
        opts = HtmlWidgetMarkdownOptions(before="", after="")
        result = build_html_widget_markdown(MINIMAL_PAYLOAD, opts)
        assert result.startswith("```html-widget\n")
        assert result.endswith("\n```")
        assert not result.startswith("\n")

    def test_handles_payload_with_undefined_optional_fields(self):
        payload = HtmlWidgetPayload(
            name="Bare",
            html="<p>minimal</p>",
            domain="https://example.com",
        )
        result = build_html_widget_markdown(payload)
        json_line = result.split("\n")[1]
        parsed = json.loads(json_line)
        assert parsed["type"] == "widget/mcp-ui"
        assert "description" not in parsed
        assert parsed["securityPolicy"] == {
            "connectDomains": [],
            "resourceDomains": ["'self'", "data:"],
            "frameDomains": [],
            "baseUriDomains": [],
        }
        assert "toolInput" not in parsed
        assert "permissions" not in parsed


# ---------------------------------------------------------------------------
# build_html_widget_message
# ---------------------------------------------------------------------------


class TestBuildHtmlWidgetMessage:
    def test_returns_message_with_extendedmarkdown_format(self):
        result = build_html_widget_message(MINIMAL_PAYLOAD)
        assert result.type == "message"
        assert result.text_format == "extendedmarkdown"

    def test_contains_widget_markdown_in_text(self):
        result = build_html_widget_message(MINIMAL_PAYLOAD)
        assert result.text == build_html_widget_markdown(MINIMAL_PAYLOAD)

    def test_passes_options_through(self):
        opts = HtmlWidgetMarkdownOptions(before="Weather today:")
        result = build_html_widget_message(FULL_PAYLOAD, opts)
        assert result.text == build_html_widget_markdown(FULL_PAYLOAD, opts)

    def test_produces_activity_like_structure(self):
        result = build_html_widget_message(MINIMAL_PAYLOAD)
        assert result.type == "message"
        assert result.text is not None
        assert result.text_format is not None


# ---------------------------------------------------------------------------
# inject_widget_protocol
# ---------------------------------------------------------------------------


class TestInjectWidgetProtocol:
    BARE_HTML = "<body><h1>Hello</h1></body>"
    BARE_HTML_NO_BODY = "<h1>Hello</h1>"

    def test_injects_protocol_before_body_close(self):
        result = inject_widget_protocol(self.BARE_HTML)
        assert "ui/initialize" in result
        assert "ui/notifications/size-changed" in result
        assert "ui/notifications/initialized" in result
        assert "</body>" in result
        script_idx = result.index("ui/initialize")
        body_idx = result.index("</body>")
        assert script_idx < body_idx

    def test_appends_script_if_no_body_tag(self):
        result = inject_widget_protocol(self.BARE_HTML_NO_BODY)
        assert "ui/initialize" in result
        assert "<h1>Hello</h1>" in result

    def test_uses_custom_name_and_version(self):
        opts = InjectWidgetProtocolOptions(name="my-widget", version="2.0.0")
        result = inject_widget_protocol(self.BARE_HTML, opts)
        assert "name:'my-widget'" in result
        assert "version:'2.0.0'" in result

    def test_uses_default_name_and_version(self):
        result = inject_widget_protocol(self.BARE_HTML)
        assert "name:'widget'" in result
        assert "version:'1.0.0'" in result

    def test_does_not_modify_html_with_existing_protocol(self):
        html_with_init = "<body><script>ui/initialize</script></body>"
        result = inject_widget_protocol(html_with_init)
        assert result == html_with_init

    def test_is_idempotent(self):
        first = inject_widget_protocol(self.BARE_HTML)
        second = inject_widget_protocol(first)
        assert second == first

    def test_handles_empty_html(self):
        result = inject_widget_protocol("")
        assert "ui/initialize" in result
        assert "<script>" in result

    def test_injects_in_full_html_document(self):
        full_doc = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><div>Content</div></body></html>'
        result = inject_widget_protocol(full_doc)
        assert "ui/initialize" in result
        content_idx = result.index("Content</div>")
        script_idx = result.index("<script>")
        body_idx = result.index("</body>")
        assert content_idx < script_idx
        assert script_idx < body_idx

    def test_matches_body_tag_naively(self):
        html = "<body><!-- </body> --><p>Real content</p></body>"
        result = inject_widget_protocol(html)
        assert "ui/initialize" in result
        script_idx = result.index("<script>")
        comment_idx = result.index("<!-- ")
        assert script_idx > comment_idx

    def test_notification_hooks_opt_in(self):
        opts = InjectWidgetProtocolOptions(notifications=["tool-result", "tool-input", "host-context-changed"])
        with_hooks = inject_widget_protocol(self.BARE_HTML, opts)
        assert "ui/notifications/tool-result" in with_hooks
        assert "window.onToolResult" in with_hooks
        assert "ui/notifications/tool-input" in with_hooks
        assert "window.onToolInput" in with_hooks
        assert "ui/notifications/host-context-changed" in with_hooks
        assert "window.onHostContextChanged" in with_hooks

        without_hooks = inject_widget_protocol(self.BARE_HTML)
        assert "onToolResult" not in without_hooks
        assert "onToolInput" not in without_hooks
        assert "onHostContextChanged" not in without_hooks

    def test_ignores_unknown_notification_names(self):
        opts = InjectWidgetProtocolOptions(notifications=["some-future-event"])
        result = inject_widget_protocol(self.BARE_HTML, opts)
        assert "ui/notifications/some-future-event" not in result
        assert "onSomeFutureEvent" not in result

    def test_all_known_notification_types(self):
        opts = InjectWidgetProtocolOptions(
            notifications=[
                "tool-result",
                "tool-input",
                "tool-input-partial",
                "tool-cancelled",
                "host-context-changed",
                "resource-teardown",
            ]
        )
        result = inject_widget_protocol(self.BARE_HTML, opts)
        assert "ui/notifications/tool-result" in result
        assert "window.onToolResult" in result
        assert "ui/notifications/tool-input-partial" in result
        assert "window.onToolInputPartial" in result
        assert "ui/notifications/tool-cancelled" in result
        assert "window.onToolCancelled" in result
        assert "ui/notifications/resource-teardown" in result
        assert "window.onResourceTeardown" in result

    def test_includes_available_display_modes(self):
        opts = InjectWidgetProtocolOptions(available_display_modes=["inline", "fullscreen"])
        result = inject_widget_protocol(self.BARE_HTML, opts)
        assert "availableDisplayModes" in result
        assert json.dumps(["inline", "fullscreen"]) in result

    def test_omits_available_display_modes_when_not_provided(self):
        result = inject_widget_protocol(self.BARE_HTML)
        assert "availableDisplayModes" not in result
        assert "appCapabilities:{}" in result


# ---------------------------------------------------------------------------
# build_html_widget_markdown integration
# ---------------------------------------------------------------------------


class TestBuildHtmlWidgetMarkdownIntegration:
    def test_injects_protocol_using_payload_name(self):
        payload = HtmlWidgetPayload(
            name="My Custom Widget",
            html="<body><p>Hello</p></body>",
            domain="https://example.com",
        )
        result = build_html_widget_markdown(payload)
        parsed = _parse_widget_json(result)
        assert "name:'My Custom Widget'" in parsed["html"]

    def test_no_double_inject_with_existing_protocol(self):
        html_with_protocol = "<body><script>ui/initialize already here</script></body>"
        payload = HtmlWidgetPayload(
            name="Test",
            html=html_with_protocol,
            domain="https://example.com",
        )
        result = build_html_widget_markdown(payload)
        parsed = _parse_widget_json(result)
        assert parsed["html"] == html_with_protocol

    def test_produces_valid_output_with_minimal_payload(self):
        payload = HtmlWidgetPayload(
            name="Bare",
            html="<p>minimal</p>",
            domain="https://example.com",
        )
        result = build_html_widget_markdown(payload)
        assert result.startswith("```html-widget\n")
        assert result.endswith("\n```")
        parsed = _parse_widget_json(result)
        assert "ui/initialize" in parsed["html"]
        assert "<p>minimal</p>" in parsed["html"]

    def test_message_with_protocol_e2e(self):
        payload = HtmlWidgetPayload(
            name="E2E Widget",
            html="<body><div>test</div></body>",
            domain="https://teams.microsoft.com",
        )
        msg = build_html_widget_message(payload)
        assert msg.type == "message"
        assert msg.text_format == "extendedmarkdown"
        assert msg.text is not None
        parsed = _parse_widget_json(msg.text)
        assert "ui/initialize" in parsed["html"]
        assert "name:'E2E Widget'" in parsed["html"]


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------


class TestPayloadValidation:
    def test_throws_if_name_empty(self):
        payload = HtmlWidgetPayload(
            name="",
            html="<div>Hello</div>",
            domain="https://example.com",
        )
        with pytest.raises(ValueError, match='non-empty "name"'):
            build_html_widget_markdown(payload)

    def test_throws_if_name_whitespace(self):
        payload = HtmlWidgetPayload(
            name="   ",
            html="<div>Hello</div>",
            domain="https://example.com",
        )
        with pytest.raises(ValueError, match='non-empty "name"'):
            build_html_widget_markdown(payload)

    def test_throws_if_html_empty(self):
        payload = HtmlWidgetPayload(
            name="Widget",
            html="",
            domain="https://example.com",
        )
        with pytest.raises(ValueError, match='non-empty "html"'):
            build_html_widget_markdown(payload)

    def test_throws_if_html_whitespace(self):
        payload = HtmlWidgetPayload(
            name="Widget",
            html="   ",
            domain="https://example.com",
        )
        with pytest.raises(ValueError, match='non-empty "html"'):
            build_html_widget_markdown(payload)

    def test_does_not_throw_for_valid_payload(self):
        build_html_widget_markdown(MINIMAL_PAYLOAD)

    def test_validates_through_build_message(self):
        payload = HtmlWidgetPayload(
            name="",
            html="<div>Hello</div>",
            domain="https://example.com",
        )
        with pytest.raises(ValueError, match='non-empty "name"'):
            build_html_widget_message(payload)

    def test_throws_if_domain_empty(self):
        payload = HtmlWidgetPayload(
            name="Widget",
            html="<div>Hello</div>",
            domain="",
        )
        with pytest.raises(ValueError, match="https://"):
            build_html_widget_markdown(payload)

    def test_throws_if_domain_not_https(self):
        payload = HtmlWidgetPayload(
            name="Widget",
            html="<div>Hello</div>",
            domain="example.com",
        )
        with pytest.raises(ValueError, match="https://"):
            build_html_widget_markdown(payload)


# ---------------------------------------------------------------------------
# validate_security_policy
# ---------------------------------------------------------------------------


class TestValidateSecurityPolicy:
    def test_no_warnings_for_no_external_references(self):
        html = "<div><p>Hello world</p></div>"
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert warnings == []

    def test_warns_script_src_not_in_resource_domains(self):
        html = '<script src="https://cdn.example.com/lib.js"></script>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"
        assert warnings[0].source == "<script src>"
        assert warnings[0].url == "https://cdn.example.com/lib.js"

    def test_no_warn_when_origin_in_resource_domains(self):
        html = '<script src="https://cdn.example.com/lib.js"></script>'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=["https://cdn.example.com"],
            frame_domains=[],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html, policy)
        assert warnings == []

    def test_warns_link_href_not_in_resource_domains(self):
        html = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto">'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"
        assert warnings[0].source == "<link href>"

    def test_warns_img_src_not_in_resource_domains(self):
        html = '<img src="https://images.example.com/photo.png">'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"
        assert warnings[0].source == "<img src>"

    def test_warns_fetch_not_in_connect_domains(self):
        html = '<script>fetch("https://api.example.com/data")</script>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "connectDomains"
        assert warnings[0].source == "fetch()"

    def test_no_warn_when_fetch_origin_in_connect_domains(self):
        html = '<script>fetch("https://api.example.com/data")</script>'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=["https://api.example.com"],
            resource_domains=[],
            frame_domains=[],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html, policy)
        assert warnings == []

    def test_warns_xhr_open_not_in_connect_domains(self):
        html = '<script>xhr.open("GET", "https://api.example.com/data")</script>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "connectDomains"
        assert warnings[0].source == "XMLHttpRequest.open()"

    def test_warns_websocket_not_in_connect_domains(self):
        html = '<script>new WebSocket("wss://ws.example.com/stream")</script>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "connectDomains"

    def test_warns_iframe_src_not_in_frame_domains(self):
        html = '<iframe src="https://embed.youtube.com/video123"></iframe>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "frameDomains"
        assert warnings[0].source == "<iframe src>"

    def test_no_warn_iframe_in_frame_domains(self):
        html = '<iframe src="https://embed.youtube.com/video123"></iframe>'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=[],
            frame_domains=["https://embed.youtube.com"],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html, policy)
        assert warnings == []

    def test_warns_css_url_not_in_resource_domains(self):
        html = '<style>body { background-image: url("https://images.example.com/bg.png"); }</style>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"
        assert warnings[0].source == "CSS url()"

    def test_warns_css_import_not_in_resource_domains(self):
        html = '<style>@import "https://fonts.googleapis.com/css2?family=Roboto";</style>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"
        assert warnings[0].source == "CSS @import"

    def test_warns_form_action_not_in_connect_domains(self):
        html = '<form action="https://api.example.com/submit"><input type="text"></form>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "connectDomains"
        assert warnings[0].source == "<form action>"

    def test_no_warn_form_action_in_connect_domains(self):
        html = '<form action="https://api.example.com/submit"><input type="text"></form>'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=["https://api.example.com"],
            resource_domains=[],
            frame_domains=[],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html, policy)
        assert warnings == []

    def test_warns_event_source_not_in_connect_domains(self):
        html = '<script>new EventSource("https://sse.example.com/events")</script>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "connectDomains"
        assert warnings[0].source == "new EventSource()"

    def test_warns_audio_src_not_in_resource_domains(self):
        html = '<audio src="https://media.example.com/song.mp3"></audio>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"
        assert warnings[0].source == "<audio src>"

    def test_warns_video_src_not_in_resource_domains(self):
        html = '<video src="https://media.example.com/clip.mp4"></video>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"
        assert warnings[0].source == "<video src>"

    def test_ignores_relative_urls(self):
        html = '<img src="./logo.png"><script src="/app.js"></script>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert warnings == []

    def test_ignores_data_uris(self):
        html = '<img src="data:image/png;base64,abc123">'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert warnings == []

    def test_detects_multiple_violations(self):
        html = (
            '<script src="https://cdn.example.com/lib.js"></script>'
            '<script>fetch("https://api.example.com/data")</script>'
            '<iframe src="https://embed.example.com/widget"></iframe>'
        )
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 3
        fields = sorted(w.policy_field for w in warnings)
        assert fields == ["connectDomains", "frameDomains", "resourceDomains"]

    def test_handles_wildcard_in_policy(self):
        html = '<script src="https://any-cdn.com/lib.js"></script>'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=["*"],
            frame_domains=[],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html, policy)
        assert warnings == []

    def test_handles_protocol_relative_urls(self):
        html = '<script src="//cdn.example.com/lib.js"></script>'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "resourceDomains"

    def test_handles_undefined_policy_fields(self):
        html = '<script src="https://cdn.example.com/lib.js"></script>'
        policy = HtmlWidgetSecurityPolicy()
        warnings = validate_security_policy(html, policy)
        assert len(warnings) == 1


# ---------------------------------------------------------------------------
# debugCspViolations
# ---------------------------------------------------------------------------


class TestDebugCspViolations:
    def test_injects_csp_listener_when_enabled(self):
        opts = InjectWidgetProtocolOptions(debug_csp_violations=True)
        result = inject_widget_protocol("<body><p>Hello</p></body>", opts)
        assert "securitypolicyviolation" in result
        assert "blockedURI" in result
        assert "violatedDirective" in result

    def test_does_not_inject_by_default(self):
        result = inject_widget_protocol("<body><p>Hello</p></body>")
        assert "securitypolicyviolation" not in result

    def test_does_not_inject_when_explicitly_false(self):
        opts = InjectWidgetProtocolOptions(debug_csp_violations=False)
        result = inject_widget_protocol("<body><p>Hello</p></body>", opts)
        assert "securitypolicyviolation" not in result


class TestScriptInjectionPrevention:
    def test_escapes_script_close_tag_in_name(self):
        """Prevents </script> in name from breaking out of the inline script."""
        opts = InjectWidgetProtocolOptions(name="</script><img src=x onerror=alert(1)>")
        result = inject_widget_protocol("<body></body>", opts)
        # Only one </script> should exist (the injected protocol's closing tag)
        import re

        script_tags = re.findall(r"</script>", result, re.IGNORECASE)
        assert len(script_tags) == 1
        assert "<\\/script>" in result

    def test_escapes_script_close_tag_in_version(self):
        """Prevents </script> in version from breaking out."""
        opts = InjectWidgetProtocolOptions(version='</script><svg onload=fetch("/steal")>')
        result = inject_widget_protocol("<body></body>", opts)
        import re

        script_tags = re.findall(r"</script>", result, re.IGNORECASE)
        assert len(script_tags) == 1

    def test_escapes_newlines_in_name(self):
        """Prevents newlines from breaking JS string literals."""
        opts = InjectWidgetProtocolOptions(name="line1\nline2\rline3")
        result = inject_widget_protocol("<body></body>", opts)
        # Extract script content
        import re

        script_match = re.search(r"<script>(.*?)</script>", result, re.DOTALL | re.IGNORECASE)
        assert script_match is not None
        script_content = script_match.group(1)
        # No raw newlines inside the script
        assert "\n" not in script_content
        assert "\\n" in script_content
        assert "\\r" in script_content


class TestOptionsImmutability:
    def test_does_not_mutate_protocol_options(self):
        """buildHtmlWidgetMarkdown should not mutate the caller's protocolOptions."""
        proto_opts = InjectWidgetProtocolOptions(version="2.0.0", notifications=["tool-result"])
        options = HtmlWidgetMarkdownOptions(protocol_options=proto_opts)
        payload = HtmlWidgetPayload(
            name="MutationTest",
            html="<body>hi</body>",
            domain="https://example.com",
        )
        build_html_widget_markdown(payload, options)
        # The original proto_opts.name should remain unchanged
        assert proto_opts.name is None


class TestProtocolVersion:
    def test_embeds_correct_mcp_protocol_version(self):
        result = inject_widget_protocol("<body></body>")
        assert "protocolVersion:'2026-01-26'" in result


class TestSubdomainMatching:
    def test_allows_subdomain_when_parent_in_policy(self):
        html = '<script src="https://cdn.example.com/lib.js"></script>'
        warnings = validate_security_policy(html, HtmlWidgetSecurityPolicy(resource_domains=["https://example.com"]))
        assert len(warnings) == 0

    def test_does_not_allow_unrelated_domain_sharing_suffix(self):
        html = '<script src="https://notexample.com/lib.js"></script>'
        warnings = validate_security_policy(html, HtmlWidgetSecurityPolicy(resource_domains=["https://example.com"]))
        assert len(warnings) == 1


class TestUnicodeInWidgetName:
    def test_passes_unicode_through_correctly(self):
        opts = InjectWidgetProtocolOptions(name="Widget \u2764\ufe0f")
        result = inject_widget_protocol("<body></body>", opts)
        assert "name:'Widget \u2764\ufe0f'" in result


class TestSnapshotFullInjectedScript:
    def test_matches_expected_protocol_script_output(self, snapshot):
        opts = InjectWidgetProtocolOptions(
            name="My Widget",
            version="2.0.0",
            available_display_modes=["inline", "fullscreen"],
            notifications=["tool-result", "tool-input"],
            debug_csp_violations=True,
        )
        result = inject_widget_protocol("<body><h1>Hello</h1></body>", opts)

        import re

        match = re.search(r"<script>(.*?)</script>", result, re.DOTALL)
        assert match is not None
        assert match.group(1) == snapshot
