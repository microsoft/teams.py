"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from datetime import datetime

from microsoft.teams.api import AdaptiveCardInvokeActivity, MessageActivity, MessageActivityInput
from microsoft.teams.api.models.adaptive_card import (
    AdaptiveCardActionMessageResponse,
)
from microsoft.teams.api.models.invoke_response import AdaptiveCardInvokeResponse
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.cards import (
    ActionSet,
    AdaptiveCard,
    ExecuteAction,
    NumberInput,
    OpenUrlAction,
    SubmitActionData,
    TextBlock,
    ToggleInput,
)
from microsoft.teams.cards.core import Choice, ChoiceSetInput, DateInput, TextInput

app = App()


def create_basic_adaptive_card() -> AdaptiveCard:
    """Create a basic adaptive card for testing."""
    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="Hello world", wrap=True, weight="Bolder"),
            ToggleInput(label="Notify me").with_id("notify"),
            ActionSet(
                actions=[
                    ExecuteAction(title="Submit")
                    .with_data(SubmitActionData("submit_basic"))
                    .with_associated_inputs("auto")
                ]
            ),
        ],
    )
    return card


def create_model_validate_card() -> AdaptiveCard:
    """Create an adaptive card using model_validate to test deserialization."""
    card = AdaptiveCard.model_validate(
        {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "verticalContentAlignment": "center",
                            "items": [
                                {
                                    "type": "Image",
                                    "style": "Person",
                                    "url": "https://aka.ms/AAp9xo4",
                                    "size": "Small",
                                    "altText": "Portrait of David Claux",
                                }
                            ],
                            "width": "auto",
                        },
                        {
                            "type": "Column",
                            "spacing": "medium",
                            "verticalContentAlignment": "center",
                            "items": [{"type": "TextBlock", "weight": "Bolder", "text": "David Claux", "wrap": True}],
                            "width": "auto",
                        },
                        {
                            "type": "Column",
                            "spacing": "medium",
                            "verticalContentAlignment": "center",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "Principal Platform Architect at Microsoft",
                                    "isSubtle": True,
                                    "wrap": True,
                                }
                            ],
                            "width": "stretch",
                        },
                    ],
                }
            ],
            "version": "1.5",
        }
    )
    return card


def create_profile_card() -> AdaptiveCard:
    """Create a profile card with input validation from documentation."""
    profile_card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="User Profile", weight="Bolder", size="Large"),
            TextInput(id="name").with_label("Name").with_value("John Doe"),
            TextInput(id="email", label="Email", value="john@contoso.com"),
            ToggleInput(title="Subscribe to newsletter").with_id("subscribe").with_value("false"),
            ActionSet(
                actions=[
                    ExecuteAction(title="Save")
                    .with_data(SubmitActionData("save_profile", {"entity_id": "12345"}))
                    .with_associated_inputs("auto"),
                    OpenUrlAction(url="https://adaptivecards.microsoft.com").with_title("Learn More"),
                ]
            ),
        ],
    )
    return profile_card


def create_profile_card_input_validation() -> AdaptiveCard:
    """Create a profile card with input validation from documentation."""
    age_input = NumberInput(id="age").with_label("Age").with_is_required(True).with_min(0).with_max(120)
    name_input = TextInput(id="name").with_label("Name").with_is_required(True).with_error_message("Name is required")

    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="Profile with Validation", weight="Bolder", size="Large"),
            age_input,
            name_input,
            TextInput(id="location").with_label("Location"),
            ActionSet(
                actions=[
                    ExecuteAction(title="Save").with_data({"action": "save_profile"}).with_associated_inputs("auto")
                ]
            ),
        ],
    )
    return card


def create_feedback_card() -> AdaptiveCard:
    """Create a feedback card for testing actions."""
    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="Feedback Form", weight="Bolder", size="Large"),
            TextInput(id="feedback")
            .with_label("Your Feedback")
            .with_placeholder("Please share your thoughts...")
            .with_is_multiline(True)
            .with_is_required(True),
            ActionSet(
                actions=[
                    ExecuteAction(title="Submit Feedback")
                    .with_data(SubmitActionData("submit_feedback"))
                    .with_associated_inputs("auto")
                ]
            ),
        ],
    )
    return card


@app.on_message_pattern("card")
async def handle_card_message(ctx: ActivityContext[MessageActivity]):
    """Handle card request messages."""
    print(f"[CARD] Card requested by: {ctx.activity.from_}")
    card = create_basic_adaptive_card()
    await ctx.send(card)


@app.on_message_pattern("json")
async def handle_validate_card_message(ctx: ActivityContext[MessageActivity]):
    """Handle model validation card request messages."""
    print(f"[VALIDATE] Model validate card requested by: {ctx.activity.from_}")
    card = create_model_validate_card()
    message = MessageActivityInput(text="Hello text!").add_card(card)
    await ctx.send(message)


@app.on_message_pattern("form")
async def handle_form(ctx: ActivityContext[MessageActivity]):
    card = AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        body=[
            TextBlock(text="Create New Task", weight="Bolder", size="Large"),
            TextInput(id="title").with_label("Task Title").with_placeholder("Enter task title"),
            TextInput(id="description")
            .with_label("Description")
            .with_placeholder("Enter task details")
            .with_is_multiline(True),
            ChoiceSetInput(
                choices=[
                    Choice(title="High", value="high"),
                    Choice(title="Medium", value="medium"),
                    Choice(title="Low", value="low"),
                ]
            )
            .with_id("priority")
            .with_label("Priority")
            .with_value("medium"),
            DateInput(id="due_date").with_label("Due Date").with_value(datetime.now().strftime("%Y-%m-%d")),
            ActionSet(
                actions=[
                    ExecuteAction(title="Create Task")
                    .with_data(SubmitActionData("create_task"))
                    .with_associated_inputs("auto")
                    .with_style("positive")
                ]
            ),
        ],
    )

    await ctx.send(card)


@app.on_message_pattern("profile")
async def handle_profile_card(ctx: ActivityContext[MessageActivity]):
    """Handle profile card request messages."""
    print(f"[PROFILE] Profile card requested by: {ctx.activity.from_}")
    card = create_profile_card()
    await ctx.send(card)


@app.on_message_pattern("validation")
async def handle_validation_card(ctx: ActivityContext[MessageActivity]):
    """Handle profile validation card request messages."""
    print(f"[VALIDATION] Profile validation card requested by: {ctx.activity.from_}")
    card = create_profile_card_input_validation()
    await ctx.send(card)


@app.on_message_pattern("feedback")
async def handle_feedback_card(ctx: ActivityContext[MessageActivity]):
    """Handle feedback card request messages."""
    print(f"[FEEDBACK] Feedback card requested by: {ctx.activity.from_}")
    card = create_feedback_card()
    await ctx.send(card)


@app.on_card_action("submit_basic")
async def handle_submit_basic(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Handle basic card submission."""
    data = ctx.activity.value.action.data
    print("Received submit_basic action data:", data)
    notify_value = data.get("notify", "false")
    await ctx.send(f"Basic card submitted! Notify setting: {notify_value}")
    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Action processed successfully",
    )


@app.on_card_action("submit_feedback")
async def handle_submit_feedback(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Handle feedback submission."""
    data = ctx.activity.value.action.data
    print("Received submit_feedback action data:", data)
    feedback_text = data.get("feedback", "No feedback provided")
    await ctx.send(f"Feedback received: {feedback_text}")
    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Action processed successfully",
    )


@app.on_card_action("create_task")
async def handle_create_task(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Handle task creation."""
    data = ctx.activity.value.action.data
    print("Received create_task action data:", data)
    title = data.get("title", "Untitled")
    priority = data.get("priority", "medium")
    due_date = data.get("due_date", "No date")
    await ctx.send(f"Task created!\nTitle: {title}\nPriority: {priority}\nDue: {due_date}")
    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Action processed successfully",
    )


@app.on_card_action("save_profile")
async def handle_save_profile(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Handle profile save."""
    data = ctx.activity.value.action.data
    print("Received save_profile action data:", data)
    entity_id = data.get("entity_id")
    name = data.get("name", "Unknown")
    email = data.get("email", "No email")
    subscribe = data.get("subscribe", "false")
    age = data.get("age")
    location = data.get("location", "Not specified")

    response_text = f"Profile saved!\nName: {name}\nEmail: {email}\nSubscribed: {subscribe}"
    if entity_id:
        response_text += f"\nEntity ID: {entity_id}"
    if age:
        response_text += f"\nAge: {age}"
    if location != "Not specified":
        response_text += f"\nLocation: {location}"

    await ctx.send(response_text)
    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Action processed successfully",
    )


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle general message activities."""
    print(f"[GENERAL] Message received: {ctx.activity.text}")
    print(f"[GENERAL] From: {ctx.activity.from_}")

    if "reply" in ctx.activity.text.lower():
        await ctx.reply("Hello! How can I assist you today?")
    else:
        await ctx.send(f"You said '{ctx.activity.text}'")


if __name__ == "__main__":
    asyncio.run(app.start())
