"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os
from logging import Logger
from typing import Any, Optional

from microsoft.teams.api import (
    AdaptiveCardAttachment,
    CardTaskModuleTaskInfo,
    MessageActivity,
    MessageActivityInput,
    TaskFetchInvokeActivity,
    TaskModuleContinueResponse,
    TaskModuleMessageResponse,
    TaskModuleResponse,
    TaskSubmitInvokeActivity,
    UrlTaskModuleTaskInfo,
    card_attachment,
)
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.apps.events.types import ErrorEvent
from microsoft.teams.cards import AdaptiveCard, OpenDialogData, SubmitAction, SubmitActionData, TextBlock, TextInput
from microsoft.teams.common.logging import ConsoleLogger

logger_instance = ConsoleLogger()
logger: Logger = logger_instance.create_logger("@apps/dialogs")

if not os.getenv("BOT_ENDPOINT"):
    logger.warning("No remote endpoint detected. Using webpages for dialog will not work as expected")

app = App(client_id=os.getenv("BOT_ID"), client_secret=os.getenv("BOT_PASSWORD"))

app.page("customform", os.path.join(os.path.dirname(__file__), "views", "customform"), "/tabs/dialog-form")


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle message activities and show dialog launcher card."""

    # Create the launcher adaptive card with dialog buttons
    card = AdaptiveCard(version="1.4")
    card.body = [TextBlock(text="Select the examples you want to see!", size="Large", weight="Bolder")]

    # Use OpenDialogData to create dialog open actions with clean API
    card.actions = [
        SubmitAction(title="Simple form test").with_data(OpenDialogData("simple_form")),
        SubmitAction(title="Webpage Dialog").with_data(OpenDialogData("webpage_dialog")),
        SubmitAction(title="Multi-step Form").with_data(OpenDialogData("multi_step_form")),
    ]

    # Send the card as an attachment
    message = MessageActivityInput(text="Enter this form").add_card(card)
    await ctx.send(message)


@app.on_dialog_open("simple_form")
async def handle_simple_form_open(ctx: ActivityContext[TaskFetchInvokeActivity]):
    """Handle simple form dialog open."""
    dialog_card = AdaptiveCard.model_validate(
        {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {"type": "TextBlock", "text": "This is a simple form", "size": "Large", "weight": "Bolder"},
                {
                    "type": "Input.Text",
                    "id": "name",
                    "label": "Name",
                    "placeholder": "Enter your name",
                    "isRequired": True,
                },
            ],
            "actions": [
                # Alternative: Use SubmitActionData for cleaner action-based routing
                # SubmitAction(title="Submit").with_data(SubmitActionData("submit_simple_form"))
                {"type": "Action.Submit", "title": "Submit", "data": {"action": "submit_simple_form"}}
            ],
        }
    )

    return TaskModuleResponse(
        task=TaskModuleContinueResponse(
            value=CardTaskModuleTaskInfo(
                title="Simple Form Dialog",
                card=card_attachment(AdaptiveCardAttachment(content=dialog_card)),
            )
        )
    )


@app.on_dialog_open("webpage_dialog")
async def handle_webpage_dialog_open(ctx: ActivityContext[TaskFetchInvokeActivity]):
    """Handle webpage dialog open."""
    return TaskModuleResponse(
        task=TaskModuleContinueResponse(
            value=UrlTaskModuleTaskInfo(
                title="Webpage Dialog",
                url=f"{os.getenv('BOT_ENDPOINT', 'http://localhost:3978')}/tabs/dialog-form",
                width=1000,
                height=800,
            )
        )
    )


@app.on_dialog_open("multi_step_form")
async def handle_multi_step_form_open(ctx: ActivityContext[TaskFetchInvokeActivity]):
    """Handle multi-step form dialog open."""
    dialog_card = (
        AdaptiveCard()
        .with_body(
            [
                TextBlock(text="This is a multi-step form", size="Large", weight="Bolder"),
                TextInput(id="name").with_label("Name").with_placeholder("Enter your name").with_is_required(True),
            ]
        )
        .with_actions([SubmitAction(title="Submit").with_data(SubmitActionData("submit_multi_step_1"))])
    )

    return TaskModuleResponse(
        task=TaskModuleContinueResponse(
            value=CardTaskModuleTaskInfo(
                title="Multi-step Form Dialog",
                card=card_attachment(AdaptiveCardAttachment(content=dialog_card)),
            )
        )
    )


@app.on_dialog_submit("submit_simple_form")
async def handle_simple_form_submit(ctx: ActivityContext[TaskSubmitInvokeActivity]):
    """Handle simple form submission."""
    data: Optional[Any] = ctx.activity.value.data
    name = data.get("name") if data else None
    await ctx.send(f"Hi {name}, thanks for submitting the form!")
    return TaskModuleResponse(task=TaskModuleMessageResponse(value="Form was submitted"))


@app.on_dialog_submit("submit_webpage_dialog")
async def handle_webpage_dialog_submit(ctx: ActivityContext[TaskSubmitInvokeActivity]):
    """Handle webpage dialog submission."""
    data: Optional[Any] = ctx.activity.value.data
    name = data.get("name") if data else None
    email = data.get("email") if data else None
    await ctx.send(f"Hi {name}, thanks for submitting the form! We got that your email is {email}")
    return TaskModuleResponse(task=TaskModuleMessageResponse(value="Form submitted successfully"))


@app.on_dialog_submit("submit_multi_step_1")
async def handle_multi_step_1_submit(ctx: ActivityContext[TaskSubmitInvokeActivity]):
    """Handle multi-step form step 1 submission."""
    data: Optional[Any] = ctx.activity.value.data
    name = data.get("name") if data else None

    next_step_card = (
        AdaptiveCard()
        .with_body(
            [
                TextBlock(text="Email", size="Large", weight="Bolder"),
                TextInput(id="email").with_label("Email").with_placeholder("Enter your email").with_is_required(True),
            ]
        )
        .with_actions([SubmitAction(title="Submit").with_data(SubmitActionData("submit_multi_step_2", {"name": name}))])
    )

    return TaskModuleResponse(
        task=TaskModuleContinueResponse(
            value=CardTaskModuleTaskInfo(
                title=f"Thanks {name} - Get Email",
                card=card_attachment(AdaptiveCardAttachment(content=next_step_card)),
            )
        )
    )


@app.on_dialog_submit("submit_multi_step_2")
async def handle_multi_step_2_submit(ctx: ActivityContext[TaskSubmitInvokeActivity]):
    """Handle multi-step form step 2 submission."""
    data: Optional[Any] = ctx.activity.value.data
    name = data.get("name") if data else None
    email = data.get("email") if data else None
    await ctx.send(f"Hi {name}, thanks for submitting the form! We got that your email is {email}")
    return TaskModuleResponse(task=TaskModuleMessageResponse(value="Multi-step form completed successfully"))


@app.event("error")
async def handle_error(event: ErrorEvent) -> None:
    """Handle errors."""
    logger.error(f"Error occurred: {event.error}")
    if event.context:
        logger.warning(f"Context: {event.context}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3978))
    asyncio.run(app.start(port))
