"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Microsoft Teams Graph Integration - Demo Application

This demo shows how to use the Microsoft Graph integration with the Teams AI SDK.
It demonstrates user authentication, Graph API calls, and error handling.
"""

import asyncio

from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.api import MessageActivity
from microsoft.teams.app import ActivityContext, App, SignInEvent
from microsoft.teams.app.events.types import ErrorEvent
from microsoft.teams.graph import get_graph_client, get_user_graph_client

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities and demonstrate Graph integration."""
    message_text = ctx.activity.text.strip().lower() if ctx.activity.text else ""

    ctx.logger.info(f"Message received: {message_text}")

    # Handle different commands
    if message_text == "signin":
        await handle_signin_command(ctx)
    elif message_text == "signout":
        await handle_signout_command(ctx)
    elif message_text == "profile":
        await handle_profile_command(ctx)
    elif message_text == "emails":
        await handle_emails_command(ctx)
    elif message_text == "help":
        await handle_help_command(ctx)
    else:
        # Default response with help
        await ctx.send(
            "👋 Hello! I'm a Teams Graph demo bot.\n\n"
            "Available commands:\n"
            "• **signin** - Sign in to your Microsoft account\n"
            "• **signout** - Sign out\n"
            "• **profile** - Show your profile info\n"
            "• **emails** - List your recent emails\n"
            "• **help** - Show this help message"
        )


async def handle_signin_command(ctx: ActivityContext[MessageActivity]):
    """Handle sign-in command."""
    if ctx.is_signed_in:
        await ctx.send("✅ You are already signed in!")
    else:
        await ctx.send("🔐 Please sign in to access Microsoft Graph...")
        await ctx.sign_in()


async def handle_signout_command(ctx: ActivityContext[MessageActivity]):
    """Handle sign-out command."""
    if not ctx.is_signed_in:
        await ctx.send("ℹ️ You are not currently signed in.")
    else:
        await ctx.sign_out()
        await ctx.send("👋 You have been signed out successfully!")


async def handle_profile_command(ctx: ActivityContext[MessageActivity]):
    """Handle profile command using Graph API."""
    try:
        # Check if user is signed in
        if not ctx.is_signed_in:
            await ctx.send("🔐 Please sign in first to view your profile.")
            await ctx.sign_in()
            return

        # Get Graph client with user scopes (now synchronous)
        graph = get_user_graph_client(ctx)

        # Fetch user profile
        me = await graph.me.get()

        if me:
            profile_info = (
                f"👤 **Your Profile**\n\n"
                f"**Name:** {me.display_name or 'N/A'}\n"
                f"**Email:** {me.user_principal_name or 'N/A'}\n"
                f"**Job Title:** {me.job_title or 'N/A'}\n"
                f"**Department:** {me.department or 'N/A'}\n"
                f"**Office:** {me.office_location or 'N/A'}"
            )
            await ctx.send(profile_info)
        else:
            await ctx.send("❌ Could not retrieve your profile information.")

    except ClientAuthenticationError as e:
        ctx.logger.error(f"Authentication error: {e}")
        await ctx.send("🔐 Authentication failed. Please try signing in again.")
        await ctx.sign_in()

    except Exception as e:
        ctx.logger.error(f"Error getting profile: {e}")
        await ctx.send(f"❌ Failed to get your profile: {str(e)}")


async def handle_emails_command(ctx: ActivityContext[MessageActivity]):
    """Handle emails command using Graph API with Mail.Read scope."""
    try:
        # Check if user is signed in
        if not ctx.is_signed_in:
            await ctx.send("🔐 Please sign in first to view your emails.")
            await ctx.sign_in()
            return

        # Get Graph client (now synchronous, no scopes needed)
        graph = get_graph_client(ctx)

        # Fetch recent messages (top 5) using proper RequestConfiguration pattern
        from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder

        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["subject", "from", "receivedDateTime"], top=5
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        messages = await graph.me.messages.get(request_configuration=request_config)

        if messages and messages.value:
            email_list = "📧 **Your Recent Emails**\n\n"

            for i, message in enumerate(messages.value[:5], 1):
                subject = message.subject or "No Subject"
                sender = (
                    message.from_.email_address.name if message.from_ and message.from_.email_address else "Unknown"
                )
                received = (
                    message.received_date_time.strftime("%Y-%m-%d %H:%M") if message.received_date_time else "Unknown"
                )

                email_list += f"**{i}.** {subject}\n"
                email_list += f"   From: {sender}\n"
                email_list += f"   Received: {received}\n\n"

            await ctx.send(email_list)
        else:
            await ctx.send("📪 No recent emails found.")

    except ClientAuthenticationError as e:
        ctx.logger.error(f"Authentication error: {e}")
        await ctx.send("🔐 Authentication failed. You may need additional permissions to read emails.")

    except Exception as e:
        ctx.logger.error(f"Error getting emails: {e}")
        await ctx.send(f"❌ Failed to get your emails: {str(e)}")


async def handle_help_command(ctx: ActivityContext[MessageActivity]):
    """Handle help command."""
    help_text = (
        "🤖 **Teams Graph Demo Bot**\n\n"
        "This bot demonstrates Microsoft Graph integration with the Teams AI SDK.\n\n"
        "**Available Commands:**\n"
        "• **signin** - Sign in to your Microsoft account\n"
        "• **signout** - Sign out of your account\n"
        "• **profile** - View your Microsoft profile information\n"
        "• **emails** - List your 5 most recent emails\n"
        "• **help** - Show this help message\n\n"
        "**Getting Started:**\n"
        "1. Type `signin` to authenticate\n"
        "2. Once signed in, try `profile` or `emails`\n"
        "3. Type `signout` when you're done\n\n"
        "**Note:** This bot requires appropriate permissions to access your Microsoft Graph data."
    )
    await ctx.send(help_text)


@app.event("sign_in")
async def handle_sign_in_event(event: SignInEvent):
    """Handle successful sign-in events."""
    await event.activity_ctx.send(
        "✅ **Successfully signed in!**\n\n"
        "You can now use these commands:\n"
        "• `profile` - View your profile\n"
        "• `emails` - View your recent emails\n"
        "• `signout` - Sign out when done"
    )


@app.event("error")
async def handle_error_event(event: ErrorEvent):
    """Handle error events."""
    print(f"❌ Error occurred: {event.error}")
    if event.context:
        print(f"Context: {event.context}")


if __name__ == "__main__":
    print("🚀 Starting Teams Graph Demo Bot...")
    asyncio.run(app.start())
