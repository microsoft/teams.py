"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - messageback widget.
"""

from .runtime import build_widget_html

# MessageBack widget - sends a messageBack action to the bot.
#
# Protocol flow:
#   1. User clicks "Send MessageBack" button.
#   2. Widget sends JSON-RPC request: { method: "ui/message", params: { role, content } }
#      via window.parent.postMessage to the Teams host.
#   3. Teams delivers this as a new message activity to the bot.
#   4. Bot receives activity.value with the messageBack content.
MESSAGEBACK_WIDGET_HTML = build_widget_html(
    "MessageBack Widget",
    css="""\
h3{margin:0 0 8px 0}
p{margin:0 0 12px 0;color:#666}
button{padding:8px 16px;background:#0078d4;color:#fff;border:none;border-radius:4px;cursor:pointer}
button:hover{background:#006cbd}
#status{margin-top:12px;color:#666}""",
    body="""\
<h3>MessageBack Widget</h3>
<p>Click the button to send a messageBack to the bot.</p>
<button id="msgBtn">Send MessageBack</button>
<div id="status"></div>""",
    script="""\
document.getElementById('msgBtn').addEventListener('click', async function () {
  var status = document.getElementById('status');
  status.textContent = 'Sending messageBack...';
  var response = await window.widgetHost.request('ui/message', {
    role: 'user',
    content: [{ type: 'text', text: 'Hello from the widget!' }]
  });
  status.textContent = response.error
    ? 'Error: ' + JSON.stringify(response.error)
    : 'MessageBack sent!';
});""",
)
