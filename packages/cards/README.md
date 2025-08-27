> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams Cards

Adaptive Cards functionality for Microsoft Teams applications.
Provides utilities for creating and handling interactive card components.

## Features

- **Adaptive Card Builder**: Fluent API for creating Adaptive Cards
- **Action Handlers**: Type-safe action handling for card interactions
- **Card Templates**: Pre-built card templates for common scenarios
- **Validation**: Card schema validation and error handling
- **Teams Integration**: Seamless integration with Teams Bot Framework

## Card Creation

```python
from microsoft.teams.cards import AdaptiveCard, TextBlock, ActionSubmit

# Create an adaptive card
card = AdaptiveCard() \
    .add_item(TextBlock("Hello from Teams!")) \
    .add_action(ActionSubmit("Click Me", {"action": "hello"}))

# Send in message
await ctx.send_card(card)
```

## Action Handling

```python
@app.on_invoke("hello")
async def handle_card_action(ctx: ActivityContext[InvokeActivity]):
    # Handle card action
    await ctx.send("Card action received!")
```

## Card Types

- **Message Cards**: Rich content for bot messages
- **Task Modules**: Modal dialogs and forms
- **Tab Cards**: Content for Teams tabs
- **Connector Cards**: Webhook-based cards