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
    InvokeResponse,
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
from microsoft.teams.cards import AdaptiveCard, SubmitAction, SubmitActionData, TaskFetchSubmitActionData, TextBlock
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

    # Create the launcher adaptive card using Python objects to demonstrate SubmitActionData
    # This tests that ms_teams correctly serializes to 'msteams'
    card = AdaptiveCard(version="1.4")
    card.body = [TextBlock(text="Select the examples you want to see!", size="Large", weight="Bolder")]

    # Use SubmitActionData with ms_teams to test serialization
    # SubmitActionData uses extra="allow" to accept custom fields
    simple_form_data = SubmitActionData.model_validate({"opendialogtype": "simple_form"})
    simple_form_data.ms_teams = TaskFetchSubmitActionData().model_dump()

    webpage_data = SubmitActionData.model_validate({"opendialogtype": "webpage_dialog"})
    webpage_data.ms_teams = TaskFetchSubmitActionData().model_dump()

    multistep_data = SubmitActionData.model_validate({"opendialogtype": "multi_step_form"})
    multistep_data.ms_teams = TaskFetchSubmitActionData().model_dump()

    card.actions = [
        SubmitAction(title="Simple form test").with_data(simple_form_data),
        SubmitAction(title="Webpage Dialog").with_data(webpage_data),
        SubmitAction(title="Multi-step Form").with_data(multistep_data),
        # Keep this one as JSON to show mixed usage
        SubmitAction.model_validate(
            {
                "type": "Action.Submit",
                "title": "Mixed Example (JSON)",
                "data": {"msteams": {"type": "task/fetch"}, "opendialogtype": "mixed_example"},
            }
        ),
    ]

    # Send the card as an attachment
    message = MessageActivityInput(text="Enter this form").add_card(card)
    await ctx.send(message)


@app.on_dialog_open
async def handle_dialog_open(ctx: ActivityContext[TaskFetchInvokeActivity]):
    """Handle dialog open events for all dialog types."""
    data: Optional[Any] = ctx.activity.value.data
    dialog_type = data.get("opendialogtype") if data else None

    if dialog_type == "simple_form":
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
                    {"type": "Action.Submit", "title": "Submit", "data": {"submissiondialogtype": "simple_form"}}
                ],
            }
        )

        return InvokeResponse(
            body=TaskModuleResponse(
                task=TaskModuleContinueResponse(
                    value=CardTaskModuleTaskInfo(
                        title="Simple Form Dialog",
                        card=card_attachment(AdaptiveCardAttachment(content=dialog_card)),
                    )
                )
            )
        )

    elif dialog_type == "webpage_dialog":
        return InvokeResponse(
            body=TaskModuleResponse(
                task=TaskModuleContinueResponse(
                    value=UrlTaskModuleTaskInfo(
                        title="Webpage Dialog",
                        url=f"{os.getenv('BOT_ENDPOINT', 'http://localhost:3978')}/tabs/dialog-form",
                        width=1000,
                        height=800,
                    )
                )
            )
        )

    elif dialog_type == "multi_step_form":
        dialog_card = AdaptiveCard.model_validate(
            {
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": "This is a multi-step form", "size": "Large", "weight": "Bolder"},
                    {
                        "type": "Input.Text",
                        "id": "name",
                        "label": "Name",
                        "placeholder": "Enter your name",
                        "isRequired": True,
                    },
                ],
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Submit",
                        "data": {"submissiondialogtype": "webpage_dialog_step_1"},
                    }
                ],
            }
        )

        return InvokeResponse(
            body=TaskModuleResponse(
                task=TaskModuleContinueResponse(
                    value=CardTaskModuleTaskInfo(
                        title="Multi-step Form Dialog",
                        card=card_attachment(AdaptiveCardAttachment(content=dialog_card)),
                    )
                )
            )
        )

    # Default return for unknown dialog types
    return TaskModuleResponse(task=TaskModuleMessageResponse(value="Unknown dialog type"))


@app.on_dialog_submit
async def handle_dialog_submit(ctx: ActivityContext[TaskSubmitInvokeActivity]):
    """Handle dialog submit events for all dialog types."""
    data: Optional[Any] = ctx.activity.value.data
    dialog_type = data.get("submissiondialogtype") if data else None

    if dialog_type == "simple_form":
        name = data.get("name") if data else None
        await ctx.send(f"Hi {name}, thanks for submitting the form!")
        return TaskModuleResponse(task=TaskModuleMessageResponse(value="Form was submitted"))

    elif dialog_type == "webpage_dialog":
        name = data.get("name") if data else None
        email = data.get("email") if data else None
        await ctx.send(f"Hi {name}, thanks for submitting the form! We got that your email is {email}")
        return InvokeResponse(
            body=TaskModuleResponse(task=TaskModuleMessageResponse(value="Form submitted successfully"))
        )

    elif dialog_type == "webpage_dialog_step_1":
        name = data.get("name") if data else None
        next_step_card = AdaptiveCard.model_validate(
            {
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": "Email", "size": "Large", "weight": "Bolder"},
                    {
                        "type": "Input.Text",
                        "id": "email",
                        "label": "Email",
                        "placeholder": "Enter your email",
                        "isRequired": True,
                    },
                ],
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Submit",
                        "data": {"submissiondialogtype": "webpage_dialog_step_2", "name": name},
                    }
                ],
            }
        )

        return InvokeResponse(
            body=TaskModuleResponse(
                task=TaskModuleContinueResponse(
                    value=CardTaskModuleTaskInfo(
                        title=f"Thanks {name} - Get Email",
                        card=card_attachment(AdaptiveCardAttachment(content=next_step_card)),
                    )
                )
            )
        )

    elif dialog_type == "webpage_dialog_step_2":
        name = data.get("name") if data else None
        email = data.get("email") if data else None
        await ctx.send(f"Hi {name}, thanks for submitting the form! We got that your email is {email}")
        return InvokeResponse(
            body=TaskModuleResponse(task=TaskModuleMessageResponse(value="Multi-step form completed successfully"))
        )

    return TaskModuleResponse(task=TaskModuleMessageResponse(value="Unknown submission type"))


@app.event("error")
async def handle_error(event: ErrorEvent) -> None:
    """Handle errors."""
    logger.error(f"Error occurred: {event.error}")
    if event.context:
        logger.warning(f"Context: {event.context}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3978))
    asyncio.run(app.start(port))
