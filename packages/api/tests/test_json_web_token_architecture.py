"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Architectural test: locks the trust-boundary contract on JsonWebToken.

JsonWebToken is a typed accessor over an *already-validated* JWT payload.
Constructing it does not verify the signature. Legitimate construction sites
must either run after the HTTP-boundary validator has executed, or wrap a
token sourced from trusted identity infrastructure (MSAL, Bot Framework API
responses).

If a new file starts constructing JsonWebToken, this test fails so the
addition is reviewed against the trust-boundary contract. Add the file to
ALLOWLIST only after verifying it satisfies one of those conditions.
"""

import re
from pathlib import Path

# Path to the monorepo workspace root (teams.py).
REPO_ROOT = Path(__file__).resolve().parents[3]

ALLOWLIST = {
    # Token wrappers for MSAL / credentials acquisitions — trusted source.
    "packages/apps/src/microsoft_teams/apps/token_manager.py",
    # Wraps a token already validated by TokenValidator earlier in the
    # request pipeline (http_server.py:109 invokes validate_token before
    # the JsonWebToken construction at line 114).
    "packages/apps/src/microsoft_teams/apps/http/http_server.py",
    # Wraps user_token returned by an authenticated Teams API exchange.
    "packages/apps/src/microsoft_teams/apps/routing/activity_context.py",
}

# Match `JsonWebToken(` constructor calls. Excludes the class definition itself
# via the separate skip below.
CONSTRUCT_PATTERN = re.compile(r"\bJsonWebToken\s*\(")

SKIP_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", ".git", "build", "dist"}
DEFINITION_FILE = "packages/api/src/microsoft_teams/api/auth/json_web_token.py"


def _iter_source_files() -> list[Path]:
    sources: list[Path] = []
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        # Tests, examples, and scaffolding scripts are not part of the
        # shipped trust boundary surface.
        if any(part in {"tests", "examples", "scripts", "templates"} for part in path.parts):
            continue
        sources.append(path)
    return sources


def test_json_web_token_construction_is_allowlisted() -> None:
    offenders: list[str] = []
    for path in _iter_source_files():
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative == DEFINITION_FILE:
            continue
        contents = path.read_text(encoding="utf-8")
        if not CONSTRUCT_PATTERN.search(contents):
            continue
        if relative not in ALLOWLIST:
            offenders.append(relative)

    assert offenders == [], (
        "JsonWebToken construction found outside the allowlisted trust-boundary "
        f"sites: {offenders}. If this is intentional, verify the new site runs "
        "after a TokenValidator pass or wraps a token from trusted identity "
        "infrastructure, then add it to ALLOWLIST in this test."
    )
