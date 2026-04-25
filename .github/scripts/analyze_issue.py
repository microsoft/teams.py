"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# GitHub Issue Analysis → Teams Notification
# Analyzes newly opened GitHub issues using the GitHub Models API (GPT-4o)
# and sends a summary card + action plan to a Microsoft Teams channel.

import asyncio
import json
import os
import sys

from microsoft_teams.apps import App
from microsoft_teams.cards import (
    ActionSet,
    AdaptiveCard,
    Column,
    ColumnSet,
    Container,
    Fact,
    FactSet,
    OpenUrlAction,
    TextBlock,
)
from openai import OpenAI

TRIAGE_PROMPT = """\
You are a GitHub issue triage assistant for the Microsoft Teams Python SDK.

The SDK is a UV workspace with these packages:
- api: Core API clients, models, auth
- apps: App orchestrator, plugins, routing, events, HttpServer
- common: HTTP client abstraction, logging, storage
- cards: Adaptive cards
- ai: AI/function calling utilities
- botbuilder: Bot Framework integration plugin
- devtools: Development tools plugin
- mcpplugin: MCP server plugin
- a2aprotocol: A2A protocol plugin
- graph: Microsoft Graph integration
- openai: OpenAI integration

Analyze the issue and respond with ONLY valid JSON (no markdown fencing):
{
  "category": "bug | feature | question | docs | security",
  "severity": "critical | high | medium | low | info",
  "summary": "1-2 sentence plain-text summary of the issue",
  "affected_packages": ["list", "of", "affected", "packages"],
  "suggested_labels": ["list", "of", "suggested", "labels"]
}\
"""

SEVERITY_COLORS: dict[str, str] = {
    "critical": "Attention",
    "high": "Attention",
    "medium": "Warning",
    "low": "Good",
    "info": "Default",
}


def load_issue_from_env() -> dict:
    """Read issue details from environment variables set by the workflow."""
    number = os.environ.get("ISSUE_NUMBER")
    if not number:
        print("ERROR: ISSUE_NUMBER not set")
        sys.exit(1)

    labels_str = os.environ.get("ISSUE_LABELS", "")
    return {
        "number": int(number),
        "title": os.environ.get("ISSUE_TITLE", ""),
        "body": os.environ.get("ISSUE_BODY", "") or "",
        "author": os.environ.get("ISSUE_AUTHOR", "unknown"),
        "html_url": os.environ.get("ISSUE_HTML_URL", ""),
        "labels": [label.strip() for label in labels_str.split(",") if label.strip()],
    }


def _call_model(system_prompt: str, user_message: str) -> str:
    """Call GitHub Models API and return the response content."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set")
        sys.exit(1)

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content or ""


def _issue_as_user_message(issue: dict) -> str:
    """Format issue data as a user message for the model."""
    return (
        f"Issue #{issue['number']}: {issue['title']}\n\n"
        f"Author: {issue['author']}\n"
        f"Labels: {', '.join(issue['labels']) or 'none'}\n\n"
        f"Body:\n{issue['body'][:3000]}"
    )


def triage_issue(issue: dict) -> dict:
    """Triage the issue: category, severity, summary, etc."""
    content = _call_model(TRIAGE_PROMPT, _issue_as_user_message(issue))
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Model may wrap JSON in markdown fences — try extracting it
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
        return {
            "category": "question",
            "severity": "info",
            "summary": f"Automated triage failed to parse model response. Review issue #{issue['number']} manually.",
            "affected_packages": [],
            "suggested_labels": [],
        }


def load_copilot_analysis() -> str:
    """Read the Copilot CLI analysis from file."""
    path = os.environ.get("COPILOT_ANALYSIS_FILE", "/tmp/analysis.txt")
    if not os.path.exists(path):
        return "_No Copilot analysis available._"
    with open(path) as f:
        return f.read().strip() or "_No Copilot analysis available._"


def build_triage_card(issue: dict, triage: dict) -> AdaptiveCard:
    """Build an Adaptive Card with the triage summary."""
    repo = os.environ.get("GITHUB_UPSTREAM_REPO") or os.environ.get("GITHUB_REPOSITORY", "microsoft/teams.py")
    severity = triage.get("severity", "info")
    severity_color = SEVERITY_COLORS.get(severity, "Default")

    return AdaptiveCard(
        version="1.5",
        body=[
            TextBlock(
                text=f"{repo}#{issue['number']}: {issue['title']}",
                size="Medium",
                weight="Bolder",
                wrap=True,
            ),
            ColumnSet(
                columns=[
                    Column(
                        width="auto",
                        items=[
                            TextBlock(
                                text=triage.get("category", "unknown").upper(),
                                weight="Bolder",
                                is_subtle=True,
                                size="Small",
                            ),
                        ],
                    ),
                    Column(
                        width="auto",
                        items=[
                            TextBlock(
                                text=severity.upper(),
                                color=severity_color,
                                weight="Bolder",
                                size="Small",
                            ),
                        ],
                    ),
                    Column(
                        width="stretch",
                        items=[
                            TextBlock(
                                text=f"by @{issue['author']}",
                                is_subtle=True,
                                size="Small",
                                horizontal_alignment="Right",
                            ),
                        ],
                    ),
                ],
            ),
            Container(
                style="emphasis",
                items=[
                    TextBlock(
                        text=triage.get("summary", "No summary available."),
                        wrap=True,
                    ),
                ],
            ),
            FactSet(
                facts=[
                    Fact(
                        title="Packages",
                        value=", ".join(triage.get("affected_packages", [])) or "N/A",
                    ),
                    Fact(
                        title="Suggested labels",
                        value=", ".join(triage.get("suggested_labels", [])) or "N/A",
                    ),
                ],
            ),
            ActionSet(
                actions=[
                    OpenUrlAction(title="View Issue", url=issue["html_url"]),
                ],
            ),
        ],
    )


async def main() -> None:
    print("Loading issue from environment...")
    issue = load_issue_from_env()
    print(f"Issue #{issue['number']}: {issue['title']}")

    print("Triaging issue...")
    triage = triage_issue(issue)
    print(f"Triage: category={triage.get('category')}, severity={triage.get('severity')}")

    print("Loading Copilot analysis...")
    action_plan = load_copilot_analysis()

    print("Building triage card...")
    card = build_triage_card(issue, triage)

    conversation_id = os.environ.get("TEAMS_CONVERSATION_ID")
    if not conversation_id:
        print("ERROR: TEAMS_CONVERSATION_ID not set")
        sys.exit(1)

    app = App()
    await app.initialize()

    print("Sending triage card...")
    result = await app.send(conversation_id, card)
    print(f"Triage card sent. Activity ID: {result.id}")

    print("Sending action plan as threaded reply...")
    thread_id = f"{conversation_id};messageid={result.id}"
    result = await app.send(thread_id, action_plan)
    print(f"Action plan sent. Activity ID: {result.id}")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
