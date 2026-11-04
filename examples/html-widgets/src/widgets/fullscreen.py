"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - fullscreen widget.
"""

from .runtime import build_widget_html

# Fullscreen widget - requests fullscreen display mode from the host.
#
# Protocol flow:
#   1. User clicks "Go Fullscreen" button.
#   2. Widget sends JSON-RPC request: { method: "ui/request-display-mode", params: { mode: "fullscreen" } }
#   3. Teams expands the widget iframe to fill available space.
#   4. Host responds with the new mode, widget updates its label.
FULLSCREEN_WIDGET_HTML = build_widget_html(
    "Fullscreen Widget",
    css="""\
h3{margin:0 0 8px 0}
p{margin:0 0 12px 0;color:#666}
button{padding:8px 16px;background:#107c10;color:#fff;border:none;border-radius:4px;cursor:pointer}
button:hover{background:#0e6b0e}
#content{margin-top:12px;padding:16px;background:#f0fff0;border-radius:4px}
#modeLabel{font-weight:600}""",
    body="""\
<h3>Fullscreen Widget</h3>
<p>Click the button to request fullscreen mode from Teams.</p>
<button id="fsBtn">Go Fullscreen</button>
<div id="content">
  <p>In fullscreen mode, this widget will expand to fill the available space.</p>
  <p>Current mode: <span id="modeLabel">inline</span></p>
</div>""",
    script="""\
document.getElementById('fsBtn').addEventListener('click', function () {
  var label = document.getElementById('modeLabel');
  window.widgetHost.request('ui/request-display-mode', { mode: 'fullscreen' }).then(function (response) {
    if (response.result && response.result.mode) label.textContent = response.result.mode;
    if (response.error) label.textContent = 'Error: ' + JSON.stringify(response.error);
  });
});""",
)
