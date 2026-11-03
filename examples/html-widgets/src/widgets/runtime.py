"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Shared widget runtime: the MCP Apps handshake and the height reporter.
"""

import json
from typing import Any, Optional

# The MCP Apps protocol version used for the ui/initialize handshake.
MCP_PROTOCOL_VERSION = "2026-01-26"

# Base styles shared by every widget.
# html and body have no margin, all content lives in #root, and #root uses display:flow-root.
# The height reporter measures #root, so its height must come from its content.
# Never size the document with 100vh or height:100%.
WIDGET_BASE_CSS = """\
*{margin:0;padding:0;box-sizing:border-box}
html,body{margin:0;padding:0}
#root{display:flow-root;padding:16px;background:#fff;color:#242424;font-size:13px;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}"""

# Runtime script shared by every widget.
#
# 1. Sends ui/initialize and waits for the host response.
# 2. Sends ui/notifications/initialized.
# 3. Reports the height of #root with ui/notifications/size-changed.
#    A single ResizeObserver on #root sends the unrounded getBoundingClientRect().height
#    after the handshake and on every change.
#
# It exposes window.widgetHost with:
#   ready:   a promise resolving to the ui/initialize response.
#   request: sends a JSON-RPC request and returns a promise for the response.
#            A request with no response after 30 seconds resolves with an error response.
_RUNTIME_TEMPLATE = """\
(function () {
  var REQUEST_TIMEOUT_MS = 30000;
  var pending = {};
  var nextId = 1;

  function post(message) {
    window.parent.postMessage(Object.assign({ jsonrpc: '2.0' }, message), '*');
  }

  function request(method, params) {
    var id = 'req-' + (nextId++);
    return new Promise(function (resolve) {
      pending[id] = resolve;
      setTimeout(function () {
        if (!pending[id]) return;
        delete pending[id];
        resolve({ jsonrpc: '2.0', id: id, error: { message: 'Request timed out' } });
      }, REQUEST_TIMEOUT_MS);
      post({ id: id, method: method, params: params });
    });
  }

  window.addEventListener('message', function (event) {
    var data = event.data;
    if (!data || data.jsonrpc !== '2.0' || !pending[data.id]) return;
    var resolve = pending[data.id];
    delete pending[data.id];
    resolve(data);
  });

  var root = document.getElementById('root');

  function reportSize() {
    post({
      method: 'ui/notifications/size-changed',
      params: { height: root.getBoundingClientRect().height }
    });
  }

  var ready = request('ui/initialize', {
    protocolVersion: __PROTOCOL_VERSION__,
    appInfo: { name: __APP_NAME__, version: '1.0.0' },
    appCapabilities: __APP_CAPABILITIES__
  }).then(function (response) {
    if (response.result) {
      post({ method: 'ui/notifications/initialized' });
      new ResizeObserver(reportSize).observe(root);
      reportSize();
    }
    return response;
  });

  window.widgetHost = { ready: ready, request: request };
})();"""


def _js_literal(value: Any) -> str:
    """Serialize a value as a JS literal that is safe inside an inline script element."""
    return json.dumps(value).replace("</", "<\\/")


def build_runtime_script(app_name: str, app_capabilities: Optional[dict[str, Any]] = None) -> str:
    """Build the shared runtime script for a widget named app_name."""
    return (
        _RUNTIME_TEMPLATE.replace("__PROTOCOL_VERSION__", _js_literal(MCP_PROTOCOL_VERSION))
        .replace("__APP_NAME__", _js_literal(app_name))
        .replace("__APP_CAPABILITIES__", _js_literal(app_capabilities or {}))
    )


def build_widget_html(app_name: str, css: str, body: str, script: str = "", head: str = "") -> str:
    """Assemble a widget document.

    The body markup is placed inside #root, followed by the shared runtime and then the widget's own script.
    Optional head markup is added to the document head.
    """
    widget_script = f"<script>\n{script}\n</script>\n" if script else ""
    return (
        '<!DOCTYPE html>\n<html><head><meta charset="utf-8">\n'
        f"{head}\n"
        f"<style>\n{WIDGET_BASE_CSS}\n{css}\n</style></head><body>\n"
        f'<div id="root">\n{body}\n</div>\n'
        f"<script>\n{build_runtime_script(app_name)}\n</script>\n"
        f"{widget_script}"
        "</body></html>"
    )
