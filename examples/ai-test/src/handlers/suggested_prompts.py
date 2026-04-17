"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import CardAction, CardActionType, SuggestedActions

SUGGESTED_PROMPTS = SuggestedActions(
    to=[],
    actions=[
        CardAction(type=CardActionType.IM_BACK, title="Tell me a joke", value="Tell me a joke"),
        CardAction(type=CardActionType.IM_BACK, title="What's the weather?", value="weather"),
        CardAction(type=CardActionType.IM_BACK, title="Stream a story", value="stream Tell me a short story"),
    ],
)
