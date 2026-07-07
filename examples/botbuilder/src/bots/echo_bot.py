"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Mapping, Optional, cast

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import InvokeResponse

OK_RESPONSE = {
    "statusCode": 200,
    "type": "application/vnd.microsoft.activity.message",
    "value": "Action processed successfully",
}


def get_value(value: object, name: str) -> Optional[Any]:
    if isinstance(value, Mapping):
        return cast(Optional[Any], value.get(name))
    return getattr(value, name, None)


class EchoBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        print("Message activity received.")
        await turn_context.send_activity(MessageFactory.text(f"BotBuilder: You said {turn_context.activity.text}"))

    async def on_invoke_activity(self, turn_context: TurnContext):
        activity = turn_context.activity
        activity_value = cast(object, activity.value)
        action = get_value(activity_value, "action")
        data = cast(dict[str, object], get_value(action, "data") or {})

        if activity.name == "adaptiveCard/action" and data.get("action") == "botbuilder_action":
            await turn_context.send_activity("BotBuilder handled the card action.")
            return InvokeResponse(status=200, body=OK_RESPONSE)

        return await super().on_invoke_activity(turn_context)
