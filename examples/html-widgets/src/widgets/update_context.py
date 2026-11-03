"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Widget HTML constants - update model context widget.
"""

from .runtime import build_widget_html

# Update Model Context widget - tests ui/update-model-context method.
# Sends structured context to the host that can be used by AI in future turns.
#
# Protocol flow:
#   1. User enters context JSON and clicks a button.
#   2. Widget sends JSON-RPC request: { method: "ui/update-model-context", params: { content, structuredContent } }
#   3. Teams host stores the context for use by AI in subsequent turns.
#   4. Host responds with success/error.
UPDATE_CONTEXT_WIDGET_HTML = build_widget_html(
    "Update Model Context Widget",
    css="""\
h3{margin:0 0 8px}
button{margin:4px 4px 4px 0;padding:6px 12px;border:1px solid #ccc;border-radius:4px;background:#f5f5f5;
  color:inherit;cursor:pointer;font-size:12px}
button:hover{background:#e0e0e0}
textarea{width:100%;height:60px;margin:8px 0;padding:8px;border:1px solid #ccc;border-radius:4px;
  font-family:monospace;font-size:11px;resize:none}
#status{margin-top:12px;padding:8px;background:#f0f9ff;border-radius:4px;white-space:pre-wrap;
  font-family:monospace;font-size:11px}""",
    body="""\
<h3>Update Model Context Widget</h3>
<p>Tests <code>ui/update-model-context</code> - sends context for AI to use in future turns.</p>
<textarea id="contextInput">{"userPreference": "dark mode", "currentPage": "settings"}</textarea>
<div>
  <button id="structuredBtn">Send Structured Context</button>
  <button id="textBtn">Send Text Context</button>
  <button id="bothBtn">Send Both</button>
</div>
<div id="status">Waiting...</div>""",
    script="""\
var statusEl = document.getElementById('status');

function readContext() {
  try {
    return JSON.parse(document.getElementById('contextInput').value);
  } catch (e) {
    statusEl.textContent = 'Invalid JSON in textarea';
    return null;
  }
}

async function send(params, label, success) {
  statusEl.textContent = label;
  var response = await window.widgetHost.request('ui/update-model-context', params);
  statusEl.textContent = response.error ? 'Error: ' + JSON.stringify(response.error) : success;
}

document.getElementById('structuredBtn').addEventListener('click', function () {
  var parsed = readContext();
  if (parsed === null) return;
  send(
    { structuredContent: parsed },
    'Sending structured context...',
    'Success! Context updated with structured data.'
  );
});

document.getElementById('textBtn').addEventListener('click', function () {
  send(
    { content: [{ type: 'text', text: 'User is viewing the settings page and prefers dark mode.' }] },
    'Sending text context...',
    'Success! Context updated with text content.'
  );
});

document.getElementById('bothBtn').addEventListener('click', function () {
  var parsed = readContext();
  if (parsed === null) return;
  send(
    { content: [{ type: 'text', text: 'User updated their preferences.' }], structuredContent: parsed },
    'Sending both text + structured context...',
    'Success! Context updated with both text and structured data.'
  );
});""",
)
