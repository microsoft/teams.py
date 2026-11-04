"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import ast
import importlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SAMPLE_SRC = Path(__file__).resolve().parents[3] / "examples" / "html-widgets" / "src"
REQUIRED_METHODS = ("ui/initialize", "ui/notifications/initialized", "ui/notifications/size-changed")
SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL | re.IGNORECASE)


def _load_sample_widgets() -> dict[str, str]:
    sys.path.insert(0, str(SAMPLE_SRC))
    try:
        spec = importlib.util.spec_from_file_location(
            "html_widgets_sample_widgets",
            SAMPLE_SRC / "widgets" / "__init__.py",
            submodule_search_locations=[str(SAMPLE_SRC / "widgets")],
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SAMPLE_SRC))
    return {name: value for name, value in vars(module).items() if name.endswith("_WIDGET_HTML")}


WIDGETS = _load_sample_widgets()


def test_all_eight_sample_widgets_found():
    assert len(WIDGETS) == 8


@pytest.mark.parametrize("name", sorted(WIDGETS))
def test_widget_owns_handshake_and_size_reporting(name: str):
    html = WIDGETS[name]
    for method in REQUIRED_METHODS:
        assert method in html, f"{name} is missing {method}"
    assert "2026-01-26" in html
    assert "ResizeObserver" in html
    assert "getBoundingClientRect().height" in html
    assert "scrollHeight" not in html
    assert "100vh" not in html


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("name", sorted(WIDGETS))
def test_widget_inline_scripts_are_well_formed(name: str, tmp_path: Path):
    scripts = SCRIPT_RE.findall(WIDGETS[name])
    assert scripts, f"{name} has no inline script"
    for index, script in enumerate(scripts):
        path = tmp_path / f"{name}_{index}.js"
        path.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"{name} script {index}: {result.stderr}"


def _load_widget_arguments():
    source = (SAMPLE_SRC / "main.py").read_text(encoding="utf-8")
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "_widget_arguments")
    namespace: dict = {"Any": object, "cast": lambda _t, v: v}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "main.py", "exec"), namespace)
    return namespace["_widget_arguments"]


def test_sample_handler_strips_msteams_metadata():
    widget_arguments = _load_widget_arguments()
    assert widget_arguments({"a": 1, "__msteams__": {"mcpUrl": "x"}}) == {"a": 1}
    assert widget_arguments(None) == {}


@pytest.mark.parametrize("bad", ["text", ["a"], 5, True])
def test_sample_handler_rejects_non_object_arguments(bad):
    widget_arguments = _load_widget_arguments()
    with pytest.raises(ValueError):
        widget_arguments(bad)


_HARNESS = """
const posted = [];
const listeners = [];
const parent = {};
globalThis.window = {
  parent: { postMessage: (m) => posted.push(m) },
  addEventListener: (_t, fn) => listeners.push(fn),
};
globalThis.ResizeObserver = class { observe() {} };
globalThis.document = { getElementById: () => ({ getBoundingClientRect: () => ({ height: 10 }) }) };
%(script)s
const reply = (data) => listeners.forEach((fn) => fn({ source: window.parent, data }));
const tick = () => new Promise((r) => setImmediate(r));
(async () => {
  const early = window.widgetHost.request('tools/call', {});
  await tick();
  const beforeInit = posted.filter((m) => m.method === 'tools/call').length;
  reply({ jsonrpc: '2.0', id: posted[0].id, %(init)s });
  await tick();
  const afterInit = posted.filter((m) => m.method === 'tools/call');
  if (afterInit.length) reply({ jsonrpc: '2.0', id: afterInit[0].id, result: {} });
  const response = await early;
  console.log(JSON.stringify({ beforeInit, afterInit: afterInit.length, ok: !!response.result }));
  process.exit(0);
})();
"""


def _run_harness(tmp_path: Path, init: str) -> dict:
    sys.path.insert(0, str(SAMPLE_SRC))
    try:
        runtime = importlib.import_module("widgets.runtime")
    finally:
        sys.path.remove(str(SAMPLE_SRC))
    path = tmp_path / "harness.js"
    path.write_text(_HARNESS % {"script": runtime.build_runtime_script("t"), "init": init}, encoding="utf-8")
    result = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_widget_host_request_waits_for_successful_initialization(tmp_path: Path):
    outcome = _run_harness(tmp_path, "result: { protocolVersion: '2026-01-26' }")
    assert outcome == {"beforeInit": 0, "afterInit": 1, "ok": True}


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_widget_host_request_does_not_send_after_failed_initialization(tmp_path: Path):
    outcome = _run_harness(tmp_path, "error: { message: 'nope' }")
    assert outcome == {"beforeInit": 0, "afterInit": 0, "ok": False}
