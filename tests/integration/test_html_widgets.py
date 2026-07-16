"""Integration test for HTML widget messages (send smoke test)."""

import warnings

import pytest
from conftest import TestFixture
from microsoft_teams.api.activities import MessageActivityInput
from microsoft_teams.api.models.html_widget import (
    HtmlWidgetPayload,
    HtmlWidgetPermissions,
    HtmlWidgetSecurityPolicy,
)
from microsoft_teams.apps.utils.html_widget import HtmlWidgetMarkdownOptions, build_html_widget_markdown

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
