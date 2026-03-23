# Proactive Messaging Example

This example demonstrates how to send proactive messages to Teams users without running a server. This is useful for:
- Scheduled notifications
- Alert systems
- Background jobs that need to notify users
- Webhook handlers that send messages

## Key Concepts

- Uses `app.initialize()` instead of `app.start()` (no HTTP server)
- Directly sends messages using `app.send()`
- Requires a conversation ID (from previous interactions or from the Teams API)

## How It Works

The example shows the separation of activity sending from HTTP transport:

1. **Initialize without server**: `await app.initialize()` sets up credentials, token manager, and activity sender without starting the HTTP server
2. **Send messages**: `await app.send(conversation_id, message)` sends messages directly using the ActivitySender
3. **No HTTP server**: Perfect for background jobs, scheduled tasks, or webhook handlers

## Usage

```bash
# Set up your environment variables
export CLIENT_ID=your_app_id
export CLIENT_SECRET=your_app_secret
export TENANT_ID=your_tenant_id

# Run the example with a conversation ID
uv run src/main.py <conversation_id>
```

## Getting a Conversation ID

You need a conversation ID to send proactive messages. You can get this from:

1. **Previous bot interactions**: Store the conversation ID when users first interact with your bot
2. **Teams API**: Use the Microsoft Teams API to create or get conversation references
3. **Testing**: Use an existing bot conversation and extract the conversation ID from the activity

## Example Output

```
Initializing app (without starting server)...
✓ App initialized

Sending proactive message to conversation: 19:...
Message: Hello! This is a proactive message sent without a running server 🚀
✓ Message sent successfully! Activity ID: 1234567890

Sending proactive card to conversation: 19:...
✓ Card sent successfully! Activity ID: 1234567891

✓ All proactive messages sent successfully!
```
