"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - open link widget.
"""

from .runtime import build_widget_html

# Open Link widget - tests ui/open-link method.
# Clicking a button asks the host to open a URL in the user's browser.
#
# Protocol flow:
#   1. User clicks a button with a URL.
#   2. Widget sends JSON-RPC request: { method: "ui/open-link", params: { url } }
#   3. Teams host opens the URL in the user's default browser.
#   4. Host responds with success/error.
OPEN_LINK_WIDGET_HTML = build_widget_html(
    "Open Link Widget",
    css="""\
h3{margin:0 0 8px}
button{margin:4px 4px 4px 0;padding:6px 12px;border:1px solid #ccc;border-radius:4px;background:#f5f5f5;
  color:inherit;cursor:pointer;font-size:12px}
button:hover{background:#e0e0e0}
#status{margin-top:12px;padding:8px;background:#f0f9ff;border-radius:4px;white-space:pre-wrap;
  font-family:monospace;font-size:11px}""",
    body="""\
<h3>Open Link Widget</h3>
<p>Tests the <code>ui/open-link</code> method (host opens a URL).</p>
<div style="margin-top:12px">
  <button data-url="https://github.com/modelcontextprotocol/ext-apps">Open MCP Apps Repo</button>
  <button data-url="https://learn.microsoft.com/en-us/microsoftteams/">Open Teams Docs</button>
  <button data-url="not-a-valid-url">Open Invalid URL (error test)</button>
</div>
<div id="status">Waiting...</div>""",
    script="""\
async function openLink(url) {
  var el = document.getElementById('status');
  el.textContent = 'Opening: ' + url + '...';
  var response = await window.widgetHost.request('ui/open-link', { url: url });
  el.textContent = response.error
    ? 'Error: ' + JSON.stringify(response.error)
    : 'Success! Host opened: ' + url;
}

document.querySelectorAll('[data-url]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    openLink(btn.getAttribute('data-url'));
  });
});""",
)
