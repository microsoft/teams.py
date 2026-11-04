"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - calltool widget.
"""

from .runtime import build_widget_html

# CallTool widget - calls a "refresh" tool on the bot and displays the result.
#
# Protocol flow:
#   1. User clicks "Refresh" button.
#   2. Widget sends JSON-RPC request: { method: "tools/call", params: { name: "refresh" } }
#      via window.parent.postMessage to the Teams host.
#   3. Teams routes this as an htmlwidget/calltool invoke activity to the bot.
#      The client adds arguments.__msteams__ = { mcpUrl, correlationId } to the request.
#   4. Bot handles the invoke and returns a CallToolResult.
#   5. Teams delivers the result back to the widget iframe as a JSON-RPC response.
#   6. Widget updates the UI with the result.
CALLTOOL_WIDGET_HTML = build_widget_html(
    "CallTool Widget",
    css="""\
h3{margin:0 0 8px 0}
p{margin:0 0 12px 0;color:#666}
button{padding:8px 16px;background:#5b5fc7;color:#fff;border:none;border-radius:4px;cursor:pointer}
button:hover{background:#4b4fb7}
#result{margin-top:12px;padding:8px;background:#f5f5f5;border-radius:4px}""",
    body="""\
<h3>CallTool Widget</h3>
<p>Click Refresh to call the bot's "refresh" tool.</p>
<button id="refreshBtn">Refresh</button>
<div id="result">Waiting for action...</div>""",
    script="""\
document.getElementById('refreshBtn').addEventListener('click', function () {
  var result = document.getElementById('result');
  result.textContent = 'Calling refresh...';
  window.widgetHost.request('tools/call', { name: 'refresh', arguments: {} }).then(function (response) {
    result.textContent = response.error
      ? 'Error: ' + JSON.stringify(response.error)
      : JSON.stringify(response.result);
  });
});""",
)
