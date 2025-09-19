> [!CAUTION]
> This project is in public preview. We’ll do our best to maintain compatibility, but there may be breaking changes in upcoming releases. 

# Microsoft Teams Cards

<p>
    <a href="https://pypi.org/project/microsoft-teams-cards" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-cards" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-cards" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-cards" />
    </a>
</p>

Adaptive Cards models and specialized action types for Microsoft Teams applications.
Provides Pydantic-based models for creating Adaptive Cards and Teams-specific actions.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

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
