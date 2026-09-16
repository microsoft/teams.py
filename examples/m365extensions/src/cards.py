"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from microsoft_teams.cards.core import (
    AdaptiveCard,
    Fact,
    FactSet,
    SubmitAction,
    TextBlock,
    TextInput,
)
from microsoft_teams.cards.utilities import OpenDialogData


def help_card() -> AdaptiveCard:
    return AdaptiveCard(
        version="1.5",
        body=[
            TextBlock(text="Teams SDK Feature Showcase", weight="Bolder", size="Large"),
            TextBlock(
                text="Teams SDK handlers (TEAMS_APP)",
                weight="Bolder",
                spacing="Medium",
            ),
            FactSet(
                facts=[
                    Fact(title="help", value="This command list"),
                    Fact(title="react", value="Bot adds/removes emoji reactions"),
                    Fact(title="quote", value="Bot quotes its own message"),
                    Fact(title="targeted", value="Ephemeral message visible only to sender"),
                    Fact(title="task", value="Task module fetch/submit flow"),
                ]
            ),
            TextBlock(
                text="Agents SDK fallthrough handlers (AGENT_SDK_APP)",
                weight="Bolder",
                spacing="Medium",
            ),
            FactSet(
                facts=[
                    Fact(title="agents sdk react", value="Reach teams.py's API client from an Agents SDK handler"),
                    Fact(title="agents sdk proactive", value="Trigger a proactive send from an Agents SDK handler"),
                    Fact(title="channel", value="Report the channel this turn arrived on and how it was routed"),
                    Fact(title="anything else", value="Echo via Agents SDK '[Agent SDK] You said: ...'"),
                ]
            ),
        ],
    )


def task_launcher_card() -> AdaptiveCard:
    """Card whose button opens a task module via the task/fetch invoke."""
    return AdaptiveCard(
        version="1.5",
        body=[
            TextBlock(text="📋 Task module demo", weight="Bolder"),
            TextBlock(
                text="Press the button to open a task module.",
                wrap=True,
            ),
        ],
        actions=[
            SubmitAction(title="Open task module").with_data(OpenDialogData("open_task")),
        ],
    )


def task_form_card() -> AdaptiveCard:
    """The form shown inside the task module."""
    return AdaptiveCard(
        version="1.5",
        body=[
            TextBlock(text="Tell us something:", weight="Bolder"),
            TextInput(id="note").with_placeholder("Type here…"),
        ],
        actions=[SubmitAction(title="Submit")],
    )
