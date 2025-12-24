"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import MagicMock

import pytest
from microsoft_teams.api import (
    Account,
    AdaptiveCardInvokeActivity,
    AdaptiveCardInvokeResponse,
    ConversationAccount,
)
from microsoft_teams.api.models.adaptive_card import (
    AdaptiveCardActionMessageResponse,
    AdaptiveCardInvokeAction,
    AdaptiveCardInvokeValue,
)
from microsoft_teams.apps import ActivityContext, App


class TestCardActionExecuteRouting:
    """Test cases for card action execute routing functionality."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage."""
        return MagicMock()

    @pytest.fixture(scope="function")
    def app_with_options(self, mock_logger, mock_storage):
        """Create an app with basic options."""
        return App(
            logger=mock_logger,
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
        )

    def test_on_card_action_execute_with_action_id(self, app_with_options: App) -> None:
        """Test on_card_action_execute with specific action matching."""

        @app_with_options.on_card_action_execute("submit_form")
        async def handle_submit_form(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
            return AdaptiveCardActionMessageResponse(
                status_code=200, type="application/vnd.microsoft.activity.message", value="Form submitted"
            )

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test matching action
        matching_activity = AdaptiveCardInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "submit_form"})
            ),
        )

        # Test non-matching action
        non_matching_activity = AdaptiveCardInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "other_action"})
            ),
        )

        # Verify handler was registered and can match
        handlers = app_with_options.router.select_handlers(matching_activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_submit_form

        # Verify non-matching action doesn't match
        non_matching_handlers = app_with_options.router.select_handlers(non_matching_activity)
        assert len(non_matching_handlers) == 0

    def test_on_card_action_execute_global_handler(self, app_with_options: App) -> None:
        """Test on_card_action_execute without action matches all Action.Execute actions."""

        @app_with_options.on_card_action_execute()
        async def handle_all_actions(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
            return AdaptiveCardActionMessageResponse(
                status_code=200, type="application/vnd.microsoft.activity.message", value="Action received"
            )

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test with any action
        activity1 = AdaptiveCardInvokeActivity(
            id="test-activity-id-1",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "action1"})
            ),
        )

        activity2 = AdaptiveCardInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "action2"})
            ),
        )

        # Both should match the global handler
        handlers1 = app_with_options.router.select_handlers(activity1)
        assert len(handlers1) == 1
        assert handlers1[0] == handle_all_actions

        handlers2 = app_with_options.router.select_handlers(activity2)
        assert len(handlers2) == 1
        assert handlers2[0] == handle_all_actions

    def test_on_card_action_execute_multiple_specific_handlers(self, app_with_options: App) -> None:
        """Test multiple specific action handlers coexist correctly."""

        @app_with_options.on_card_action_execute("submit_form")
        async def handle_submit_form(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
            return AdaptiveCardActionMessageResponse(
                status_code=200, type="application/vnd.microsoft.activity.message", value="Form submitted"
            )

        @app_with_options.on_card_action_execute("save_data")
        async def handle_save_data(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
            return AdaptiveCardActionMessageResponse(
                status_code=200, type="application/vnd.microsoft.activity.message", value="Data saved"
            )

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        submit_activity = AdaptiveCardInvokeActivity(
            id="test-activity-id-1",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "submit_form"})
            ),
        )

        save_activity = AdaptiveCardInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "save_data"})
            ),
        )

        # Each should match only its specific handler
        submit_handlers = app_with_options.router.select_handlers(submit_activity)
        assert len(submit_handlers) == 1
        assert submit_handlers[0] == handle_submit_form

        save_handlers = app_with_options.router.select_handlers(save_activity)
        assert len(save_handlers) == 1
        assert save_handlers[0] == handle_save_data

    def test_on_card_action_execute_decorator_syntax(self, app_with_options: App) -> None:
        """Test on_card_action_execute works with decorator syntax."""

        @app_with_options.on_card_action_execute("test_action")
        async def decorated_handler(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
            return AdaptiveCardActionMessageResponse(
                status_code=200, type="application/vnd.microsoft.activity.message", value="Decorated"
            )

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = AdaptiveCardInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "test_action"})
            ),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == decorated_handler

    def test_on_card_action_execute_non_decorator_syntax(self, app_with_options: App) -> None:
        """Test on_card_action_execute works with non-decorator syntax."""

        async def handler_function(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
            return AdaptiveCardActionMessageResponse(
                status_code=200, type="application/vnd.microsoft.activity.message", value="Non-decorated"
            )

        app_with_options.on_card_action_execute("non_decorated_action", handler_function)

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = AdaptiveCardInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"action": "non_decorated_action"})
            ),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == handler_function

    def test_on_card_action_execute_missing_action_field(self, app_with_options: App) -> None:
        """Test on_card_action_execute handler doesn't match when action field is missing."""

        @app_with_options.on_card_action_execute("submit_form")
        async def handle_submit_form(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
            return AdaptiveCardActionMessageResponse(
                status_code=200, type="application/vnd.microsoft.activity.message", value="Form submitted"
            )

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Activity with no action field in data
        activity = AdaptiveCardInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="adaptiveCard/action",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=AdaptiveCardInvokeValue(
                action=AdaptiveCardInvokeAction(type="Action.Execute", data={"other_field": "value"})
            ),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 0
