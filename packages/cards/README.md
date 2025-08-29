> [!CAUTION]
> This project is in active development and not ready for production use. It has not been publicly announced yet.

# Microsoft Teams Cards

Adaptive Cards models and specialized action types for Microsoft Teams applications.
Provides Pydantic-based models for creating Adaptive Cards and Teams-specific actions.

## Features

- **Adaptive Card Models**: Pydantic models for Adaptive Card schema
- **Teams Actions**: Specialized action types for Teams interactions

## Basic Usage

```python
from microsoft.teams.cards import AdaptiveCard, TextBlock, SubmitAction

# Create adaptive card components
card = AdaptiveCard(
    body=[
        TextBlock(text="Hello from Teams!")
    ],
    actions=[
        SubmitAction(title="Click Me", data={"action": "hello"})
    ]
)
```

## Teams-Specific Actions

```python
from microsoft.teams.cards import InvokeAction, MessageBackAction, SignInAction

# Create Teams-specific actions
invoke_action = InvokeAction({"action": "getData"})
message_action = MessageBackAction("Send Message", {"text": "Hello"})
signin_action = SignInAction()
```
