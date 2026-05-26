# Example: Targeted Messages

A bot that demonstrates targeted (ephemeral) messages in Microsoft Teams.

Targeted messages are messages that only a specific recipient can see - other participants in the conversation won't see them.

## Commands

| Command | Behavior |
|---------|----------|
| `test send` | Sends a targeted message (only you see it) |
| `test reply` | Replies with a targeted message |
| `test update` | Sends a targeted message, then updates it after 3 seconds |
| `test delete` | Sends a targeted message, then deletes it after 5 seconds |
| `send public` | Only sends a public message if the incoming message is targeted |
| `send private` | Only sends a private message if the incoming message is targeted |
| `help` | Shows available commands |

## How It Works

When sending targeted messages explicitly, use `with_recipient(Account(...), is_targeted=True)` to mark the recipient as targeted.

When the inbound message is targeted at the bot, `ctx.send()` and `ctx.reply()` default to targeted for the same conversation. Pass a non-targeted recipient (for example, `with_recipient(ctx.activity.from_)`) to opt out and send publicly.

## Testing in a Group Chat

To properly test targeted messages:

1. Add the bot to a **group chat** with 2+ people
2. Send `test send`, or invoke `send private` as a targeted/slash command
3. **Expected result**: 
   - You (the sender) should see the targeted message
   - Other participants should **NOT** see it

The `send public` and `send private` commands are useful for verifying whether the inbound message was targeted. If it isn't, the bot says `Send it to me privately first!`.

## Run

```bash
cd examples/targeted-messages
uv run python src/main.py
```

## Environment Variables

Create a `.env` file:

```env
CLIENT_ID=<your-azure-bot-app-id>
CLIENT_SECRET=<your-azure-bot-app-secret>
```
