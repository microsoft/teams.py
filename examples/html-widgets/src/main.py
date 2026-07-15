"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

HTML Widgets Example Bot

This example demonstrates the full HTML widget capabilities for Teams bots.
Each command shows a different widget feature that developers can use as
a reference for building their own widget-enabled bots.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any

from microsoft_teams.api import HtmlWidgetCallToolInvokeActivity, MessageActivity
from microsoft_teams.api.activities.message import MessageActivityInput
from microsoft_teams.api.models.html_widget import (
    HtmlWidgetCallToolResponse,
    HtmlWidgetPayload,
    HtmlWidgetSecurityPolicy,
    McpUiCallToolResult,
    McpUiTextContent,
)
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.apps.utils.html_widget import (
    HtmlWidgetMarkdownOptions,
    build_html_widget_markdown,
    build_html_widget_message,
    validate_security_policy,
)
from widgets import (
    CALLTOOL_WIDGET_HTML,
    FULLSCREEN_WIDGET_HTML,
    HOST_CONTEXT_WIDGET_HTML,
    MESSAGEBACK_WIDGET_HTML,
    MULTI_WIDGET_HTML,
    OPEN_LINK_WIDGET_HTML,
    SIMPLE_WIDGET_HTML,
    UPDATE_CONTEXT_WIDGET_HTML,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App()


# ---------------------------------------------------------------------------
# Message commands
# ---------------------------------------------------------------------------


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Route message commands to the appropriate widget demo."""
    if not ctx.activity.text:
        return
    text = ctx.activity.text.strip().lower()

    # Simple static widget - no callbacks
    if text == "/simple":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="Simple Widget",
                description="A static HTML widget with no callbacks.",
                html=SIMPLE_WIDGET_HTML,
                domain="https://teams.microsoft.com",
                security_policy=HtmlWidgetSecurityPolicy(
                    connect_domains=[],
                    resource_domains=["'self'", "data:"],
                    frame_domains=[],
                    base_uri_domains=[],
                ),
            ),
            HtmlWidgetMarkdownOptions(
                before="Here is a simple static widget:",
                after="No callbacks needed for static content.",
            ),
        )
        await ctx.send(message)
        return

    # Widget with onCallTool callback
    if text == "/calltool":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="CallTool Widget",
                description="Widget that calls tools on the bot.",
                html=CALLTOOL_WIDGET_HTML,
                domain="https://teams.microsoft.com",
                security_policy=HtmlWidgetSecurityPolicy(
                    connect_domains=[
                        "https://teams.microsoft.com",
                        "https://teams.cloud.microsoft.com",
                    ],
                    resource_domains=["'self'", "data:"],
                    frame_domains=[],
                    base_uri_domains=[],
                ),
                tool_input={"demo": True},  # Passed to the widget as initial context (available via toolInput in ui/initialize)
                tool_output={
                    "content": [{"type": "text", "text": "Initial data loaded."}],
                    "structuredContent": {"counter": 0, "lastAction": "init"},
                    "isError": False,
                },
            ),
            HtmlWidgetMarkdownOptions(before="Here is a widget with callTool support (click Refresh):"),
        )
        await ctx.send(message)
        return

    # Widget with onMessage (messageBack) callback
    if text == "/messageback":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="MessageBack Widget",
                description="Widget that sends messageBack to the bot.",
                html=MESSAGEBACK_WIDGET_HTML,
                domain="https://teams.microsoft.com",
                security_policy=HtmlWidgetSecurityPolicy(
                    connect_domains=[],
                    resource_domains=["'self'", "data:"],
                    frame_domains=[],
                    base_uri_domains=[],
                ),
            ),
            HtmlWidgetMarkdownOptions(before="This widget tests the onMessage (messageBack) callback:"),
        )
        await ctx.send(message)
        return

    # Widget requesting fullscreen display mode
    if text == "/fullscreen":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="Fullscreen Widget",
                description="Widget that requests fullscreen mode.",
                html=FULLSCREEN_WIDGET_HTML,
                domain="https://teams.microsoft.com",
                security_policy=HtmlWidgetSecurityPolicy(
                    connect_domains=[],
                    resource_domains=["'self'", "data:"],
                    frame_domains=[],
                    base_uri_domains=[],
                ),
            ),
            HtmlWidgetMarkdownOptions(before="This widget will request fullscreen mode:"),
        )
        await ctx.send(message)
        return

    # Widget with multiple tools
    if text == "/multi":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="Multi-Tool Widget",
                description="Widget that calls multiple different tools.",
                html=MULTI_WIDGET_HTML,
                domain="https://teams.microsoft.com",
                security_policy=HtmlWidgetSecurityPolicy(
                    connect_domains=["https://teams.microsoft.com"],
                    resource_domains=["'self'", "data:"],
                    frame_domains=[],
                    base_uri_domains=[],
                ),
                tool_input={},  # Passed to the widget as initial context (available via toolInput in ui/initialize)
                tool_output={
                    "content": [{"type": "text", "text": "Ready."}],
                    "structuredContent": {"tools": ["getTime", "roll", "echo"]},
                    "isError": False,
                },
            ),
            HtmlWidgetMarkdownOptions(before="This widget has multiple tools to test dispatch:"),
        )
        await ctx.send(message)
        return

    # Widget using ui/open-link
    if text == "/openlink":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="open-link-test",
                html=OPEN_LINK_WIDGET_HTML,
                domain="https://teams.microsoft.com",
            ),
            HtmlWidgetMarkdownOptions(before="Widget with ui/open-link support (click a button to open a URL):"),
        )
        await ctx.send(message)
        return

    # Widget using ui/update-model-context
    if text == "/context":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="update-context-test",
                html=UPDATE_CONTEXT_WIDGET_HTML,
                domain="https://teams.microsoft.com",
            ),
            HtmlWidgetMarkdownOptions(before="Widget with ui/update-model-context support:"),
        )
        await ctx.send(message)
        return

    # Host context inspector
    if text == "/hostcontext":
        message = build_html_widget_message(
            HtmlWidgetPayload(
                name="host-context-inspector",
                html=HOST_CONTEXT_WIDGET_HTML,
                domain="https://teams.microsoft.com",
            ),
            HtmlWidgetMarkdownOptions(before="Widget that inspects hostContext from ui/initialize:"),
        )
        await ctx.send(message)
        return

    # Security policy validation demo
    if text == "/validate":
        html_with_external_refs = (
            '<link rel="stylesheet" '
            'href="https://fonts.googleapis.com/css2?family=Roboto">'
            '<div style="font-family: Roboto, sans-serif; padding: 16px;">'
            "<h2>Validation Demo</h2>"
            "<p>This widget was validated before sending.</p>"
            "</div>"
        )

        # Step 1: validate against a restrictive policy to catch issues
        strict_policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=["'self'", "data:"],
            frame_domains=[],
            base_uri_domains=[],
        )
        warnings = validate_security_policy(html_with_external_refs, strict_policy)

        # Step 2: fix the policy based on warnings, then build the widget
        corrected_policy = HtmlWidgetSecurityPolicy(
            connect_domains=[],
            resource_domains=[
                "'self'",
                "data:",
                "https://fonts.googleapis.com",
            ],
            frame_domains=[],
            base_uri_domains=[],
        )
        warning_text = "\n".join(f"- **{w.source}**: `{w.url}` not in `{w.policy_field}`" for w in warnings)
        markdown = build_html_widget_markdown(
            HtmlWidgetPayload(
                name="Validated Widget",
                description="Widget built after security policy validation.",
                html=html_with_external_refs,
                domain="https://teams.microsoft.com",
                security_policy=corrected_policy,
            ),
            HtmlWidgetMarkdownOptions(
                before=(
                    f"**Validation found {len(warnings)} warning(s):**\n\n"
                    + warning_text
                    + "\n\nPolicy was corrected before sending:"
                ),
            ),
        )
        await ctx.send(MessageActivityInput(text=markdown, text_format="extendedmarkdown"))
        return

    # Help
    if text in ("/help", "help"):
        await ctx.send(
            MessageActivityInput(
                text_format="markdown",
                text=(
                    "**HTML Widget Test Commands:**\n\n"
                    "- `/simple` - Static widget (no callbacks)\n"
                    "- `/calltool` - Widget with onCallTool\n"
                    "- `/messageback` - Widget with onMessage\n"
                    "- `/fullscreen` - Widget requesting fullscreen\n"
                    "- `/multi` - Widget with multiple tools\n"
                    "- `/openlink` - Widget with ui/open-link\n"
                    "- `/context` - Widget with ui/update-model-context\n"
                    "- `/hostcontext` - Inspect hostContext from initialize\n"
                    "- `/validate` - Security policy validation demo\n"
                    "- `/help` - This message"
                ),
            )
        )
        return

    # Handle messageBack values from the messageback widget
    if ctx.activity.value:
        await ctx.send(f"Received messageBack value: {json.dumps(ctx.activity.value)}")
        return

    await ctx.send("Send `/help` for available widget test commands.")


# ---------------------------------------------------------------------------
# Handle htmlwidget/calltool invoke
# This is the typed handler for when a widget calls a tool on the bot.
# ---------------------------------------------------------------------------


@app.on_widget_call_tool
async def handle_widget_call_tool(
    ctx: ActivityContext[HtmlWidgetCallToolInvokeActivity],
) -> HtmlWidgetCallToolResponse:
    """Handle widget tool calls."""
    tool_name = ctx.activity.value.name
    args: dict[str, Any] = ctx.activity.value.arguments or {}
    logger.info(f"[widget.callTool] tool={tool_name!r} args={json.dumps(args)}")

    call_tool_result: McpUiCallToolResult

    if tool_name == "refresh":
        counter = int(args.get("counter", 0) or 0) + 1
        call_tool_result = McpUiCallToolResult(
            content=[McpUiTextContent(type="text", text="Refreshed!")],
            structured_content={
                "counter": counter,
                "lastAction": "refresh",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
            is_error=False,
        )

    elif tool_name == "getTime":
        now = datetime.now(tz=timezone.utc)
        call_tool_result = McpUiCallToolResult(
            content=[McpUiTextContent(type="text", text=now.strftime("%H:%M:%S"))],
            structured_content={"time": now.isoformat()},
            is_error=False,
        )

    elif tool_name == "roll":
        sides = int(args.get("sides", 6) or 6)
        result = random.randint(1, sides)  # noqa: S311
        call_tool_result = McpUiCallToolResult(
            content=[McpUiTextContent(type="text", text=f"Rolled a {result} (d{sides})")],
            structured_content={"result": result, "sides": sides},
            is_error=False,
        )

    elif tool_name == "echo":
        call_tool_result = McpUiCallToolResult(
            content=[McpUiTextContent(type="text", text=json.dumps(args))],
            structured_content=args,
            is_error=False,
        )

    else:
        call_tool_result = McpUiCallToolResult(
            content=[McpUiTextContent(type="text", text=f"Unknown tool: {tool_name}")],
            is_error=True,
        )

    logger.info(f"[widget.callTool] result={call_tool_result}")

    return HtmlWidgetCallToolResponse(
        response_type="htmlwidget/calltoolresult",
        call_tool_result=call_tool_result,
    )


if __name__ == "__main__":
    asyncio.run(app.start())
