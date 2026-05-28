"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import json
import logging
import warnings

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.api.activities.invoke.suggested_action_submit import SuggestedActionSubmitInvokeActivity
from microsoft_teams.api.models.card.card_action import CardAction
from microsoft_teams.api.models.card.card_action_type import CardActionType
from microsoft_teams.api.models.suggested_actions import SuggestedActions
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.common.experimental import ExperimentalWarning

# Surface SDK INFO/WARNING logs (including the anonymous-mode startup warning
# emitted when CLIENT_ID / CLIENT_SECRET / TENANT_ID are not configured).
logging.basicConfig(level=logging.INFO)

# SuggestedActionSubmit and on_suggested_action_submit are marked
# @experimental("ExperimentalTeamsSuggestedAction"). See README.md.
warnings.filterwarnings("ignore", category=ExperimentalWarning, message=".*ExperimentalTeamsSuggestedAction.*")

app = App()


# Reply to any user message with two Action.Submit suggested-action chips.
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    reply = MessageActivityInput(text="Approve or reject the request:").with_suggested_actions(
        SuggestedActions(
            to=[],
            actions=[
                CardAction(type=CardActionType.SUBMIT, title="Approve", value={"vote": "approve"}),
                CardAction(type=CardActionType.SUBMIT, title="Reject", value={"vote": "reject"}),
            ],
        )
    )
    await ctx.send(reply)


# Handle the resulting suggestedActions/submit invoke when the user clicks a chip.
@app.on_suggested_action_submit
async def handle_suggested_action_submit(ctx: ActivityContext[SuggestedActionSubmitInvokeActivity]) -> None:
    serialized_value = json.dumps(ctx.activity.value)

    ctx.logger.info(f"[SUGGESTED_ACTION_SUBMIT] value={serialized_value}")
    await ctx.send(f"Got suggestedActions/submit with value: {serialized_value}")


if __name__ == "__main__":
    asyncio.run(app.start())
