"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext


class EchoBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        print("Message activity received.")
        await turn_context.send_activity(MessageFactory.text(f"Echo: {turn_context.activity.text}"))
