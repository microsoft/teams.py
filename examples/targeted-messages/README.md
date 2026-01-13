# Targeted Messages Example

This example demonstrates how to send targeted (private) messages to specific users in Microsoft Teams group chats and channels.

## Features

- Send private messages visible only to a specific user
- Reply privately to messages
- Update and delete targeted messages
- Works in group chats and channels

## Running the Example

```bash
cd examples/targeted-messages
uv run python src/main.py
```

## Usage

In a group chat or channel, mention the bot with one of these commands:

- `@bot targeted` - Sends a private message only visible to you
- `@bot targeted-reply` - Replies privately to your message
- `@bot targeted-update` - Sends a private message, then updates it
- `@bot targeted-delete` - Sends a private message, then deletes it

## How It Works

Targeted messages use the `targeted_recipient_id` parameter to specify which user should see the message:

```python
# Send a targeted message to the user who sent the activity
await ctx.send("This is private!", targeted_recipient_id=ctx.activity.from_.id)

# Reply privately
await ctx.reply("Private reply!", targeted_recipient_id=ctx.activity.from_.id)
```

The message will appear in the conversation but only the targeted recipient can see it.
