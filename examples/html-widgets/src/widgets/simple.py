"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - simple static widget.
"""

from .runtime import build_widget_html

# Simple static widget - no callbacks, no interactivity.
#
# Protocol flow:
#   1. Bot sends this HTML inside a widget/mcp-ui payload.
#   2. The shared runtime performs the MCP Apps handshake and reports the height of #root.
#   3. Teams renders the HTML in a sandboxed iframe.
SIMPLE_WIDGET_HTML = build_widget_html(
    "Simple Widget",
    css="""\
h3{margin:0 0 8px 0;color:#333}
p{margin:0;color:#666}
.status{margin-top:12px;padding:8px;background:#f0f9ff;border-radius:4px}""",
    body="""\
<h3>Simple HTML Widget</h3>
<p>This is a static HTML widget rendered inside a Teams message. No callbacks are needed.</p>
<div class="status"><strong>Status:</strong> Rendered successfully</div>""",
)
