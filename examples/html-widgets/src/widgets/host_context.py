"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - host context inspector widget.
"""

from .runtime import build_widget_html

# Host Context widget - displays the hostContext received during ui/initialize.
# Shows theme, display mode, container dimensions, locale, etc.
# Also listens for ui/notifications/host-context-changed.
#
# Protocol flow:
#   1. The shared runtime sends ui/initialize to the host.
#   2. Host responds with hostContext (theme, dimensions, locale) and hostCapabilities.
#   3. Widget displays the received context.
#   4. Widget listens for ui/notifications/host-context-changed for live updates.
HOST_CONTEXT_WIDGET_HTML = build_widget_html(
    "Host Context Inspector",
    css="""\
h3{margin:0 0 8px}
.section{margin-top:12px;padding:8px;background:#f0f9ff;border-radius:4px}
.section h4{margin:0 0 4px;font-size:12px;color:#333}
pre{white-space:pre-wrap;word-break:break-all;font-family:monospace;font-size:11px;color:#555}
.update{margin-top:8px;padding:6px;background:#fff3cd;border-radius:4px;font-size:11px}
#updates{max-height:250px;overflow-y:auto}""",
    body="""\
<h3>Host Context Inspector</h3>
<p>Displays the <code>hostContext</code> from <code>ui/initialize</code> response and listens for changes.</p>
<div class="section">
  <h4>Initialize Result</h4>
  <pre id="initResult">Waiting for initialize...</pre>
</div>
<div class="section">
  <h4>Host Context</h4>
  <pre id="hostContext">-</pre>
</div>
<div class="section">
  <h4>Host Capabilities</h4>
  <pre id="hostCaps">-</pre>
</div>
<div id="updates"></div>""",
    script="""\
window.addEventListener('message', function (event) {
  if (event.source !== window.parent) return;
  var data = event.data;
  if (!data || data.method !== 'ui/notifications/host-context-changed') return;
  var div = document.createElement('div');
  div.className = 'update';
  div.textContent = '[' + new Date().toLocaleTimeString() + '] host-context-changed: ' + JSON.stringify(data.params);
  document.getElementById('updates').appendChild(div);
  if (data.params) {
    document.getElementById('hostContext').textContent = JSON.stringify(data.params, null, 2);
  }
});

window.widgetHost.ready.then(function (response) {
  document.getElementById('initResult').textContent = JSON.stringify(response.result || response.error, null, 2);
  if (!response.result) return;
  var ctx = response.result.hostContext;
  var caps = response.result.hostCapabilities;
  document.getElementById('hostContext').textContent = ctx ? JSON.stringify(ctx, null, 2) : '(none provided)';
  document.getElementById('hostCaps').textContent = caps ? JSON.stringify(caps, null, 2) : '(none provided)';
});""",
)
