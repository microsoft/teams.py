# HTML Widgets Example

This example demonstrates the full HTML widget capabilities for Teams bots using the Python SDK.

## Demo

The bot renders several HTML widgets in Teams.
Each command below maps to a widget that exercises part of the widget contract.

### Static rendering (`/simple`)

A static widget renders directly from markdown with no callbacks.

![HTML widget simple demo: a static widget card rendered in Teams](./assets/widget-simple.png)

### Tool call round-trip (`/calltool`)

Clicking the widget button calls a bot tool via an `htmlwidget/calltool` invoke, and the widget renders the returned result.

![HTML widget callTool demo: clicking Refresh calls the bot's refresh tool and renders the result](./assets/widget-calltool.gif)

### Multi-tool dispatch (`/multi`)

The widget exposes several buttons that each dispatch to a different bot tool (getTime, roll, echo), showing per-tool arguments and results.

![HTML widget multi-tool demo: a widget with multiple buttons dispatches to different bot tools](./assets/widget-multi.gif)

### messageBack round-trip (`/messageback`)

Clicking the widget button sends a `messageBack` to the bot, which echoes the received value.

![HTML widget messageBack demo: an interactive widget card sends a messageBack that the bot echoes](./assets/widget-messageback.gif)

### Update model context (`/context`)

The widget sends structured and text context to the model using `ui/update-model-context`.

![HTML widget context demo: a widget sends update-model-context and shows a success status](./assets/widget-context.png)

### Fullscreen display mode (`/fullscreen`)

The widget requests fullscreen mode from Teams and expands to fill the available space.

![HTML widget fullscreen demo: a widget expands into a fullscreen dialog](./assets/widget-fullscreen.gif)

### Payload validation (`/validate`)

The SDK validates the widget payload before sending and reports policy warnings.

![HTML widget validation demo: a widget reports a resourceDomains policy warning that was corrected before sending](./assets/widget-validate.png)

### Host context inspection (`/hostcontext`)

The widget reads the `hostContext` from the `ui/initialize` response.

![HTML widget host context demo: a widget inspects the host context from ui/initialize](./assets/widget-hostcontext.png)

## Commands

| Command | Description |
|---------|-------------|
| `/simple` | Static widget (no callbacks) |
| `/calltool` | Widget with onCallTool (tools/call) |
| `/messageback` | Widget with onMessage (messageBack) |
| `/fullscreen` | Widget requesting fullscreen display mode |
| `/multi` | Widget with multiple tools (getTime, roll, echo) |
| `/openlink` | Widget with ui/open-link |
| `/context` | Widget with ui/update-model-context |
| `/hostcontext` | Inspect hostContext from ui/initialize |
| `/validate` | Security policy validation demo |
| `/help` | List available commands |

## Architecture

```
src/
  main.py           # Bot entry point, command routing, callTool handler
  widgets/
    __init__.py     # Re-exports all widget HTML constants
    runtime.py      # Shared handshake and size reporter, base CSS, document builder
    simple.py       # Static widget HTML
    calltool.py     # CallTool interactive widget HTML
    fullscreen.py   # Fullscreen request widget HTML
    messageback.py  # MessageBack widget HTML
    multi_tool.py   # Multi-tool dispatch widget HTML
    open_link.py    # Open link widget HTML
    update_context.py  # Update model context widget HTML
    host_context.py # Host context inspector widget HTML
```

## Running

```bash
# From the repo root
cd examples/html-widgets
cp ../../.env .env  # Or create .env with CLIENT_ID, CLIENT_SECRET, TENANT_ID

# Install dependencies (uses workspace)
uv sync

# Start the bot
uv run python src/main.py
```

## Widget Response Format

The `on_widget_call_tool` handler returns an `HtmlWidgetCallToolResponse`:

```python
@app.on_widget_call_tool
async def handle(ctx):
    return HtmlWidgetCallToolResponse(
        response_type="htmlwidget/calltoolresult",
        call_tool_result=McpUiCallToolResult(
            content=[{"type": "text", "text": "Result"}],
            structured_content={"key": "value"},
            is_error=False,
        ),
    )
```

## Key Concepts

- **`build_html_widget_message`**: Builds a complete message activity with the widget, including security policy defaults. The HTML is sent as authored.
- **`build_html_widget_markdown`**: Lower-level helper that returns the markdown string (for embedding in custom activities).
- **`validate_security_policy`**: Dev-time audit tool that checks HTML for external references not covered by the security policy.
- **Widgets own the handshake and sizing**: Each widget sends `ui/initialize` (protocolVersion `2026-01-26`, `appInfo`, `appCapabilities`), waits for the response, then sends `ui/notifications/initialized`. It then reports its height with `ui/notifications/size-changed`. Without a size reporter, Teams renders the widget at about 150px. The shared snippet lives in `src/widgets/runtime.py`.
- **Size reporter**: One `ResizeObserver` on a single root element sends the unrounded `getBoundingClientRect().height` after the handshake and on every change. The root uses `display: flow-root`, `html` and `body` have zero margin, and all content sits inside the root. Avoid `scrollHeight`, `100vh` and `height: 100%`.
- **`mcp_url` and `correlation_id`**: Optional payload fields (`mcpUrl`, `correlationId` on the wire), serialized only when set. The Teams client combines `mcpUrl` with the owner id (`<ownerId>-<mcpUrl>`) as the input for deriving the hosting origin, so a widget produced by an MCP server must set `mcpUrl` to that server's URL to get its own hosting scope, and `correlationId` as the correlation vector, which is also returned to the bot.
- **Tool results**: `McpUiCallToolResult` always emits `content` (`[]`), `structuredContent` (`{}`) and `isError` (`false`) by default, because omitted fields can reach the widget as `null`.
- **`arguments.__msteams__`**: The client adds `{ mcpUrl, correlationId }` to every `callTool` request, overwriting any bot-supplied value, and the SDK passes it through untouched. Handlers should ignore it, validate the other arguments, never throw, and not authorize from `activity.from`.
