"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - multi-tool widget.
"""

from .runtime import build_widget_html

# Multi-tool widget - calls multiple different tools on the bot.
#
# Protocol flow:
#   1. Each button sends a tools/call JSON-RPC request with a different tool name.
#   2. Teams routes each as an htmlwidget/calltool invoke activity to the bot.
#   3. The bot's widget.call_tool handler dispatches by tool name.
#   4. Results are displayed in a log panel.
MULTI_WIDGET_HTML = build_widget_html(
    "Multi-Tool Widget",
    css="""\
h3{margin:0 0 8px 0}
p{margin:0 0 12px 0;color:#666}
.tools{display:flex;gap:8px;flex-wrap:wrap}
.tools button{padding:8px 12px;color:#fff;border:none;border-radius:4px;cursor:pointer}
#log{margin-top:12px;padding:8px;background:#1e1e1e;color:#d4d4d4;border-radius:4px;
  font-family:monospace;font-size:12px;max-height:200px;overflow-y:auto;white-space:pre-wrap}""",
    body="""\
<h3>Multi-Tool Widget</h3>
<p>Each button calls a different tool on the bot.</p>
<div class="tools">
  <button data-tool="getTime" style="background:#5b5fc7">Get Time</button>
  <button data-tool="roll" data-args='{"sides":20}' style="background:#c75b5b">Roll d20</button>
  <button data-tool="echo" data-args='{"hello":"world"}' style="background:#5bc75b">Echo</button>
  <button data-tool="unknownTool" style="background:#999">Unknown (error)</button>
</div>
<div id="log">Available tools: getTime, roll, echo, unknownTool</div>""",
    script="""\
var log = document.getElementById('log');

document.querySelectorAll('[data-tool]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var tool = btn.getAttribute('data-tool');
    var args = btn.getAttribute('data-args');
    log.textContent += '\\nCalling ' + tool + '...';
    window.widgetHost.request('tools/call', {
      name: tool,
      arguments: args ? JSON.parse(args) : {}
    }).then(function (response) {
      if (response.result) log.textContent += '\\nResult: ' + JSON.stringify(response.result);
      if (response.error) log.textContent += '\\nError: ' + JSON.stringify(response.error);
    });
  });
});""",
)
