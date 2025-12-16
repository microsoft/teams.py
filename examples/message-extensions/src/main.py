"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os
from pathlib import Path
from typing import cast

from cards import (
    create_card,
    create_conversation_members_card,
    create_dummy_cards,
    create_link_unfurl_card,
    create_message_details_card,
)
from microsoft_teams.api import (
    AdaptiveCardAttachment,
    ConfigFetchInvokeActivity,
    ConfigInvokeResponse,
    ConfigSubmitInvokeActivity,
    InstalledActivity,
    InvokeResponse,
    MessageActivity,
    MessageExtensionFetchTaskInvokeActivity,
    MessageExtensionQueryInvokeActivity,
    MessageExtensionQueryLinkInvokeActivity,
    MessageExtensionQuerySettingUrlInvokeActivity,
    MessageExtensionSelectItemInvokeActivity,
    MessageExtensionSettingInvokeActivity,
    MessageExtensionSubmitActionInvokeActivity,
    TaskModuleMessageResponse,
    ThumbnailCardAttachment,
    UrlTaskModuleTaskInfo,
    card_attachment,
)
from microsoft_teams.api.models import (
    CardAction,
    CardActionType,
    CardTaskModuleTaskInfo,
    MessagingExtensionActionInvokeResponse,
    MessagingExtensionAttachment,
    MessagingExtensionAttachmentLayout,
    MessagingExtensionInvokeResponse,
    MessagingExtensionResult,
    MessagingExtensionResultType,
    MessagingExtensionSuggestedAction,
    TaskModuleContinueResponse,
)
from microsoft_teams.api.models.card.thumbnail_card import ThumbnailCard
from microsoft_teams.apps import ActivityContext, App
from typing_extensions import Any, Dict

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send('you said "' + ctx.activity.text + '"')


@app.on_install_add
async def handle_install_add(ctx: ActivityContext[InstalledActivity]):
    greeting = """
    Hi this app handles:<br>
      1. Basic message handling - echoing back what you say<br>
      2. Link unfurling - creating preview cards when you paste URLs<br>
      3. Message extension commands - handling card creation and message details.
    """
    await ctx.send(greeting)


@app.on_message_ext_query_link
async def handle_message_ext_query_link(ctx: ActivityContext[MessageExtensionQueryLinkInvokeActivity]):
    url = ctx.activity.value.url

    if not url:
        return InvokeResponse[MessagingExtensionInvokeResponse](status=400)

    card_data = create_link_unfurl_card(url)
    main_attachment = card_attachment(AdaptiveCardAttachment(content=card_data["card"]))
    preview_attachment = card_attachment(ThumbnailCardAttachment(content=card_data["thumbnail"]))

    attachment = MessagingExtensionAttachment(
        content_type=main_attachment.content_type, content=main_attachment.content, preview=preview_attachment
    )

    result = MessagingExtensionResult(
        type=MessagingExtensionResultType.RESULT,
        attachment_layout=MessagingExtensionAttachmentLayout.LIST,
        attachments=[attachment],
    )

    return MessagingExtensionInvokeResponse(compose_extension=result)


@app.on_message_ext_submit
async def handle_message_ext_submit(ctx: ActivityContext[MessageExtensionSubmitActionInvokeActivity]):
    command_id = ctx.activity.value.command_id

    if command_id == "createCard":
        card = create_card(ctx.activity.value.data or {})
    elif command_id == "getMessageDetails" and ctx.activity.value.message_payload:
        card = create_message_details_card(ctx.activity.value.message_payload)
    else:
        raise Exception(f"Unknown commandId: {command_id}")

    main_attachment = card_attachment(AdaptiveCardAttachment(content=card))
    attachment = MessagingExtensionAttachment(
        content_type=main_attachment.content_type, content=main_attachment.content
    )

    result = MessagingExtensionResult(
        type=MessagingExtensionResultType.RESULT,
        attachment_layout=MessagingExtensionAttachmentLayout.LIST,
        attachments=[attachment],
    )

    return MessagingExtensionActionInvokeResponse(compose_extension=result)


@app.on_message_ext_open
async def handle_message_ext_open(ctx: ActivityContext[MessageExtensionFetchTaskInvokeActivity]):
    conversation_id = ctx.activity.conversation.id
    members = await ctx.api.conversations.members(conversation_id).get_all()
    card = create_conversation_members_card(members)

    card_info = CardTaskModuleTaskInfo(
        title="Conversation members",
        height="small",
        width="small",
        card=card_attachment(AdaptiveCardAttachment(content=card)),
    )

    task = TaskModuleContinueResponse(value=card_info)

    return MessagingExtensionActionInvokeResponse(task=task)


@app.on_message_ext_query
async def handle_message_ext_query(ctx: ActivityContext[MessageExtensionQueryInvokeActivity]):
    command_id = ctx.activity.value.command_id
    search_query = ""
    if ctx.activity.value.parameters and len(ctx.activity.value.parameters) > 0:
        search_query = ctx.activity.value.parameters[0].value or ""

    if command_id == "searchQuery":
        cards = await create_dummy_cards(search_query)
        attachments: list[MessagingExtensionAttachment] = []
        for card_data in cards:
            main_attachment = card_attachment(AdaptiveCardAttachment(content=card_data["card"]))
            preview_attachment = card_attachment(
                ThumbnailCardAttachment(content=ThumbnailCard(**card_data["thumbnail"]))
            )

            attachment = MessagingExtensionAttachment(
                content_type=main_attachment.content_type, content=main_attachment.content, preview=preview_attachment
            )
            attachments.append(attachment)

        result = MessagingExtensionResult(
            type=MessagingExtensionResultType.RESULT,
            attachment_layout=MessagingExtensionAttachmentLayout.GRID,
            attachments=attachments,
        )

        return MessagingExtensionInvokeResponse(compose_extension=result)

    return InvokeResponse[MessagingExtensionInvokeResponse](status=400)


@app.on_message_ext_select_item
async def handle_message_ext_select_item(ctx: ActivityContext[MessageExtensionSelectItemInvokeActivity]):
    option = getattr(ctx.activity.value, "option", None)
    await ctx.send(f"Selected item: {option}")

    result = MessagingExtensionResult(
        type=MessagingExtensionResultType.RESULT,
        attachment_layout=MessagingExtensionAttachmentLayout.LIST,
        attachments=[],
    )

    return MessagingExtensionInvokeResponse(compose_extension=result)


@app.on_message_ext_query_settings_url
async def handle_message_ext_query_settings_url(ctx: ActivityContext[MessageExtensionQuerySettingUrlInvokeActivity]):
    user_settings = {"selectedOption": ""}
    escaped_selected_option = user_settings["selectedOption"]

    bot_endpoint = os.environ.get("BOT_ENDPOINT", "")

    settings_action = CardAction(
        type=CardActionType.OPEN_URL,
        title="Settings",
        value=f"{bot_endpoint}/tabs/settings?selectedOption={escaped_selected_option}",
    )

    suggested_actions = MessagingExtensionSuggestedAction(actions=[settings_action])

    result = MessagingExtensionResult(type=MessagingExtensionResultType.CONFIG, suggested_actions=suggested_actions)

    return MessagingExtensionInvokeResponse(compose_extension=result)


@app.on_message_ext_setting
async def handle_message_ext_setting(ctx: ActivityContext[MessageExtensionSettingInvokeActivity]):
    state = getattr(ctx.activity.value, "state", None)

    if state == "CancelledByUser":
        result = MessagingExtensionResult(
            type=MessagingExtensionResultType.RESULT,
            attachment_layout=MessagingExtensionAttachmentLayout.LIST,
            attachments=[],
        )
        return MessagingExtensionInvokeResponse(compose_extension=result)

    selected_option = state
    await ctx.send(f"Selected option: {selected_option}")

    result = MessagingExtensionResult(
        type=MessagingExtensionResultType.RESULT,
        attachment_layout=MessagingExtensionAttachmentLayout.LIST,
        attachments=[],
    )

    return MessagingExtensionInvokeResponse(compose_extension=result)


@app.on_config_open
async def handle_config_open(ctx: ActivityContext[ConfigFetchInvokeActivity]):
    bot_endpoint = os.environ.get("BOT_ENDPOINT", "")

    return ConfigInvokeResponse(
        config=TaskModuleContinueResponse(value=UrlTaskModuleTaskInfo(url=f"{bot_endpoint}/tabs/settings"))
    )


@app.on_config_submit
async def handle_config_submit(ctx: ActivityContext[ConfigSubmitInvokeActivity]):
    value = ctx.activity.value
    assert isinstance(value, dict), "ConfigSubmitInvokeActivity value must be a dictionary"
    state = cast(Dict[str, Any], value).get("data", None)

    return ConfigInvokeResponse(config=TaskModuleMessageResponse(value=f"Configuration saved with value: {state}"))


app.page("settings", str(Path(__file__).parent), "/tabs/settings")


if __name__ == "__main__":
    asyncio.run(app.start())
