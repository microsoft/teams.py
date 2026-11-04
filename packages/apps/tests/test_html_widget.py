"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Tests for HTML widget utilities.

import json
import warnings
from typing import Any

import pytest
from microsoft_teams.api.models.html_widget import (
    HtmlWidgetCallToolResponse,
    HtmlWidgetPayload,
    HtmlWidgetPermissions,
    HtmlWidgetSecurityPolicy,
    McpUiCallToolResult,
    McpUiTextContent,
)
from microsoft_teams.apps.utils.html_widget import (
    HtmlWidgetMarkdownOptions,
    build_html_widget_markdown,
    build_html_widget_message,
    try_get_widget_model_context,
    validate_security_policy,
)
from microsoft_teams.common.experimental import ExperimentalWarning

# Suppress ExperimentalWarning in all widget tests
warnings.filterwarnings("ignore", category=ExperimentalWarning)


class TestCallToolResultDefaults:
    def test_empty_result_serializes_defaults(self):
        dumped = McpUiCallToolResult().model_dump(by_alias=True, exclude_none=True)
        assert dumped == {"content": [], "structuredContent": {}, "isError": False}

    def test_explicit_none_falls_back_to_defaults(self):
        result = McpUiCallToolResult.model_validate({"content": None, "structuredContent": None, "isError": None})
        assert result.model_dump(by_alias=True, exclude_none=True) == {
            "content": [],
            "structuredContent": {},
            "isError": False,
        }

    def test_assigning_none_falls_back_to_defaults(self):
        result = McpUiCallToolResult()
        result.content = None  # type: ignore[assignment]
        result.structured_content = None
        result.is_error = None  # type: ignore[assignment]
        assert result.model_dump(by_alias=True, exclude_none=True) == {
            "content": [],
            "structuredContent": {},
            "isError": False,
        }

    def test_response_envelope_keeps_defaults(self):
        response = HtmlWidgetCallToolResponse(call_tool_result=McpUiCallToolResult())
        dumped = response.model_dump(by_alias=True, exclude_none=True)
        assert dumped["callToolResult"] == {"content": [], "structuredContent": {}, "isError": False}


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

    def test_sends_html_unchanged(self):
        result = build_html_widget_markdown(MINIMAL_PAYLOAD)
        parsed = _parse_widget_json(result)
        assert parsed["html"] == "<div>Hello</div>"

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

    def test_serializes_mcp_url_and_correlation_id_when_set(self):
        payload = MINIMAL_PAYLOAD.model_copy(update={"mcp_url": "mcp.example.com", "correlation_id": "abc.1"})
        parsed = _parse_widget_json(build_html_widget_markdown(payload))
        assert parsed["mcpUrl"] == "mcp.example.com"
        assert parsed["correlationId"] == "abc.1"

    def test_omits_mcp_url_and_correlation_id_when_unset(self):
        parsed = _parse_widget_json(build_html_widget_markdown(MINIMAL_PAYLOAD))
        assert "mcpUrl" not in parsed
        assert "correlationId" not in parsed

    def test_serializes_full_payload_with_all_fields(self):
        result = build_html_widget_markdown(FULL_PAYLOAD)
        parsed = _parse_widget_json(result)
        assert parsed["type"] == "widget/mcp-ui"
        assert parsed["name"] == "Weather Widget"
        assert parsed["description"] == "Current weather conditions"
        assert parsed["html"] == '<div class="weather">72F</div>'
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
# build_html_widget_markdown integration
# ---------------------------------------------------------------------------


class TestBuildHtmlWidgetMarkdownIntegration:
    def test_sends_html_unchanged(self):
        html = "<body><p>Hello</p></body>"
        payload = HtmlWidgetPayload(name="My Custom Widget", html=html, domain="https://example.com")
        parsed = _parse_widget_json(build_html_widget_markdown(payload))
        assert parsed["html"] == html

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
        assert parsed["html"] == "<p>minimal</p>"

    def test_message_e2e(self):
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
        assert parsed["html"] == "<body><div>test</div></body>"
        assert "<script>" not in parsed["html"]


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

    def test_throws_if_domain_malformed_https(self):
        for domain in ("https://", "https:// not a url", "http://example.com"):
            payload = HtmlWidgetPayload(
                name="Widget",
                html="<div>Hello</div>",
                domain=domain,
            )
            with pytest.raises(ValueError, match="https://"):
                build_html_widget_markdown(payload)

    def test_valid_https_domain_does_not_raise(self):
        payload = HtmlWidgetPayload(
            name="Widget",
            html="<div>Hello</div>",
            domain="https://teams.microsoft.com",
        )
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

    def test_warns_when_subdomain_uses_different_scheme_than_pinned_entry(self):
        html = '<script src="http://cdn.example.com/lib.js"></script>'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=["https://example.com"],
            frame_domains=[],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html, policy)
        assert len(warnings) == 1
        assert warnings[0].url == "http://cdn.example.com/lib.js"

    def test_allows_any_scheme_for_host_only_entry(self):
        html = '<script src="http://cdn.example.com/lib.js"></script>'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=["example.com"],
            frame_domains=[],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html, policy)
        assert warnings == []

    def test_warns_base_href_not_in_base_uri_domains(self):
        html = '<base href="https://evil.example.com/">'
        warnings = validate_security_policy(html, EMPTY_POLICY)
        assert len(warnings) == 1
        assert warnings[0].policy_field == "baseUriDomains"
        assert warnings[0].source == "<base href>"
        assert warnings[0].url == "https://evil.example.com/"

    def test_no_warn_base_href_in_base_uri_domains(self):
        html = '<base href="https://cdn.example.com/">'
        policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=[],
            frame_domains=[],
            base_uri_domains=["https://cdn.example.com"],
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


class TestSubdomainMatching:
    def test_allows_subdomain_when_parent_in_policy(self):
        html = '<script src="https://cdn.example.com/lib.js"></script>'
        warnings = validate_security_policy(html, HtmlWidgetSecurityPolicy(resource_domains=["https://example.com"]))
        assert len(warnings) == 0

    def test_does_not_allow_unrelated_domain_sharing_suffix(self):
        html = '<script src="https://notexample.com/lib.js"></script>'
        warnings = validate_security_policy(html, HtmlWidgetSecurityPolicy(resource_domains=["https://example.com"]))
        assert len(warnings) == 1


# ---------------------------------------------------------------------------
# try_get_widget_model_context
# ---------------------------------------------------------------------------


class _FakeActivity:
    def __init__(self, value: Any):
        self.value = value


class TestTryGetWidgetModelContext:
    def test_parses_raw_request(self):
        activity = _FakeActivity(
            {
                "method": "ui/update-model-context",
                "params": {"content": [{"type": "text", "text": "hello"}]},
            }
        )
        result = try_get_widget_model_context(activity)
        assert result is not None
        assert result.method == "ui/update-model-context"
        assert result.params.content is not None
        first = result.params.content[0]
        assert isinstance(first, McpUiTextContent)
        assert first.text == "hello"

    def test_parses_structured_content_only(self):
        activity = _FakeActivity(
            {
                "method": "ui/update-model-context",
                "params": {"structuredContent": {"count": 5}},
            }
        )
        result = try_get_widget_model_context(activity)
        assert result is not None
        assert result.params.structured_content == {"count": 5}

    def test_unwraps_widget_model_context_envelope(self):
        activity = _FakeActivity(
            {
                "type": "widgetModelContext",
                "data": {
                    "method": "ui/update-model-context",
                    "params": {"content": [{"type": "text", "text": "wrapped"}]},
                },
            }
        )
        result = try_get_widget_model_context(activity)
        assert result is not None
        assert result.params.content is not None
        first = result.params.content[0]
        assert isinstance(first, McpUiTextContent)
        assert first.text == "wrapped"

    def test_returns_none_when_value_missing(self):
        assert try_get_widget_model_context(_FakeActivity(None)) is None

    def test_returns_none_when_value_not_dict(self):
        assert try_get_widget_model_context(_FakeActivity("hello")) is None
        assert try_get_widget_model_context(_FakeActivity(42)) is None

    def test_returns_none_for_non_matching_method(self):
        activity = _FakeActivity({"method": "something/else", "params": {}})
        assert try_get_widget_model_context(activity) is None

    def test_returns_none_when_params_missing(self):
        activity = _FakeActivity({"method": "ui/update-model-context"})
        assert try_get_widget_model_context(activity) is None

    def test_returns_none_for_wrong_envelope_type(self):
        activity = _FakeActivity({"type": "other", "data": {"method": "ui/update-model-context", "params": {}}})
        assert try_get_widget_model_context(activity) is None
