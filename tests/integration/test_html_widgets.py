"""Integration tests for HTML widget messages (send, update, delete)."""

import warnings

import pytest
from microsoft_teams.api.activities import MessageActivityInput
from microsoft_teams.api.models.html_widget import (
    HtmlWidgetPayload,
    HtmlWidgetPermissions,
    HtmlWidgetSecurityPolicy,
)
from microsoft_teams.apps.utils.html_widget import HtmlWidgetMarkdownOptions, build_html_widget_markdown

from conftest import TestFixture

# Suppress experimental warnings in integration tests
warnings.filterwarnings("ignore", category=UserWarning, message=".*preview.*")


class TestHtmlWidgets:
    """Tests that verify Teams accepts widget payloads via the Bot API."""

    @pytest.mark.asyncio
    async def test_send_widget_message(self, fixture: TestFixture):
        """Send a widget message with extendedmarkdown textFormat."""
        if not fixture.is_canary:
            pytest.skip("Widgets require canary service")

        markdown = build_html_widget_markdown(
            HtmlWidgetPayload(
                name="Integration Test Widget",
                description="Verifies Teams accepts widget payload.",
                html="<body><p>Integration test widget</p></body>",
                domain="https://teams.microsoft.com",
                security_policy=HtmlWidgetSecurityPolicy(
                    connect_domains=[],
                    resource_domains=["'self'", "data:"],
                    frame_domains=[],
                    base_uri_domains=[],
                ),
                permissions=HtmlWidgetPermissions(),
            ),
            HtmlWidgetMarkdownOptions(before="[PY Integration] HTML widget send test"),
        )

        result = await fixture.api.conversations.activities(fixture.config.conversation_id).create(
            MessageActivityInput().with_text(markdown).with_text_format("extendedmarkdown")
        )
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_send_widget_with_tool_data(self, fixture: TestFixture):
        """Send a widget message with toolInput and toolOutput fields."""
        if not fixture.is_canary:
            pytest.skip("Widgets require canary service")

        markdown = build_html_widget_markdown(
            HtmlWidgetPayload(
                name="ToolOutput Widget",
                description="Widget with initial tool data.",
                html="<body><p>Widget with tool data</p></body>",
                domain="https://teams.microsoft.com",
                security_policy=HtmlWidgetSecurityPolicy(
                    connect_domains=[],
                    resource_domains=["'self'"],
                    frame_domains=[],
                    base_uri_domains=[],
                ),
                tool_input={"query": "test"},
                tool_output={
                    "content": [{"type": "text", "text": "Result data"}],
                    "structured_content": {"key": "value"},
                    "is_error": False,
                },
                permissions=HtmlWidgetPermissions(clipboard_write={}),
            ),
        )

        result = await fixture.api.conversations.activities(fixture.config.conversation_id).create(
            MessageActivityInput().with_text(markdown).with_text_format("extendedmarkdown")
        )
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_update_widget_message(self, fixture: TestFixture):
        """Send then update a widget message."""
        if not fixture.is_canary:
            pytest.skip("Widgets require canary service")

        markdown = build_html_widget_markdown(
            HtmlWidgetPayload(
                name="Update Test Widget",
                html="<body><p>Original content</p></body>",
                domain="https://teams.microsoft.com",
            ),
            HtmlWidgetMarkdownOptions(before="[PY Integration] Widget update test - original"),
        )

        sent = await fixture.api.conversations.activities(fixture.config.conversation_id).create(
            MessageActivityInput().with_text(markdown).with_text_format("extendedmarkdown")
        )
        assert sent.id is not None

        updated_markdown = build_html_widget_markdown(
            HtmlWidgetPayload(
                name="Update Test Widget",
                html="<body><p>Updated content</p></body>",
                domain="https://teams.microsoft.com",
            ),
            HtmlWidgetMarkdownOptions(before="[PY Integration] Widget update test - updated"),
        )

        await fixture.api.conversations.activities(fixture.config.conversation_id).update(
            sent.id, MessageActivityInput().with_text(updated_markdown).with_text_format("extendedmarkdown")
        )

    @pytest.mark.asyncio
    async def test_delete_widget_message(self, fixture: TestFixture):
        """Send then delete a widget message."""
        if not fixture.is_canary:
            pytest.skip("Widgets require canary service")

        markdown = build_html_widget_markdown(
            HtmlWidgetPayload(
                name="Delete Test Widget",
                html="<body><p>Will be deleted</p></body>",
                domain="https://teams.microsoft.com",
            ),
        )

        sent = await fixture.api.conversations.activities(fixture.config.conversation_id).create(
            MessageActivityInput().with_text(markdown).with_text_format("extendedmarkdown")
        )
        assert sent.id is not None

        await fixture.api.conversations.activities(fixture.config.conversation_id).delete(sent.id)

