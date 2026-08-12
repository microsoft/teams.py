"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).parent
TOKEN_URL = "https://directline.botframework.com/v3/directline/tokens/generate"
PORT = int(os.environ.get("PORT", "3000"))


def _load_secret() -> str:
    secret = os.environ.get("DIRECTLINE_SECRET", "")
    env_file = HERE / ".env"
    if not secret and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DIRECTLINE_SECRET="):
                secret = line.split("=", 1)[1].strip()
                break
    if not secret:
        raise SystemExit(
            "DIRECTLINE_SECRET is not set. Export it, or write it to "
            f"{env_file} as DIRECTLINE_SECRET=<secret>.\n"
            "Fetch it with:\n"
            "  az bot directline show --name <botName> --resource-group <rg> "
            "--with-secrets -o json"
        )
    return secret


SECRET = _load_secret()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        if self.path.startswith("/api/token"):
            req = urllib.request.Request(
                TOKEN_URL,
                method="POST",
                data=b"",
                headers={"Authorization": f"Bearer {SECRET}"},
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    payload = resp.read()
            except Exception as exc:  # surface the failure in the browser
                self._send(502, json.dumps({"error": str(exc)}).encode(), "application/json")
                return
            self._send(200, payload, "application/json")
            return

        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            return

        self._send(404, b"not found", "text/plain")

    def log_message(self, fmt: str, *args) -> None:
        print(f"[webchat] {fmt % args}")


if __name__ == "__main__":
    print(f"[webchat] serving http://localhost:{PORT}  (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
