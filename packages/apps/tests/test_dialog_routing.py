"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import MagicMock

import pytest
from microsoft.teams.api import (
    Account,
    AdaptiveCardAttachment,
    CardTaskModuleTaskInfo,
    ConversationAccount,
    InvokeResponse,
    TaskFetchInvokeActivity,
    TaskModuleContinueResponse,
    TaskModuleMessageResponse,
    TaskModuleRequest,
    TaskModuleResponse,
    TaskSubmitInvokeActivity,
    card_attachment,
)
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.cards import AdaptiveCard


class TestDialogRouting:
    """Test cases for dialog routing functionality."""

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

    def test_on_dialog_open_with_dialog_id(self, app_with_options: App) -> None:
        """Test on_dialog_open with specific dialog_id matching."""

        @app_with_options.on_dialog_open("test_dialog")
        async def handle_test_dialog(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Test dialog opened"))

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test matching dialog_id
        matching_activity = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "test_dialog"}),
        )

        # Test non-matching dialog_id
        non_matching_activity = TaskFetchInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "other_dialog"}),
        )

        # Verify handler was registered and can match
        handlers = app_with_options.router.select_handlers(matching_activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_test_dialog

        # Verify non-matching dialog_id doesn't match
        non_matching_handlers = app_with_options.router.select_handlers(non_matching_activity)
        assert len(non_matching_handlers) == 0

    def test_on_dialog_open_global_handler(self, app_with_options: App) -> None:
        """Test on_dialog_open without dialog_id matches all dialog opens."""

        @app_with_options.on_dialog_open()
        async def handle_all_dialogs(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Any dialog opened"))

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test with dialog_id present
        activity_with_id = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "some_dialog"}),
        )

        # Test without dialog_id
        activity_without_id = TaskFetchInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={}),
        )

        # Both should match global handler
        handlers_with_id = app_with_options.router.select_handlers(activity_with_id)
        assert len(handlers_with_id) == 1
        assert handlers_with_id[0] == handle_all_dialogs

        handlers_without_id = app_with_options.router.select_handlers(activity_without_id)
        assert len(handlers_without_id) == 1
        assert handlers_without_id[0] == handle_all_dialogs

    def test_on_dialog_open_with_non_dict_data(self, app_with_options: App) -> None:
        """Test on_dialog_open handles non-dict data gracefully."""

        @app_with_options.on_dialog_open("test_dialog")
        async def handle_test_dialog(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Test"))

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test with non-dict data (should not match)
        activity = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data="not a dict"),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 0

    def test_on_dialog_submit_with_action(self, app_with_options: App) -> None:
        """Test on_dialog_submit with specific action matching."""

        @app_with_options.on_dialog_submit("submit_form")
        async def handle_form_submit(ctx: ActivityContext[TaskSubmitInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Form submitted"))

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test matching action
        matching_activity = TaskSubmitInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/submit",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"action": "submit_form", "name": "John"}),
        )

        # Test non-matching action
        non_matching_activity = TaskSubmitInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="task/submit",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"action": "cancel_form"}),
        )

        # Verify handler was registered and can match
        handlers = app_with_options.router.select_handlers(matching_activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_form_submit

        # Verify non-matching action doesn't match
        non_matching_handlers = app_with_options.router.select_handlers(non_matching_activity)
        assert len(non_matching_handlers) == 0

    def test_on_dialog_submit_global_handler(self, app_with_options: App) -> None:
        """Test on_dialog_submit without action matches all dialog submits."""

        @app_with_options.on_dialog_submit()
        async def handle_all_submits(ctx: ActivityContext[TaskSubmitInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Any submit"))

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test with action present
        activity_with_action = TaskSubmitInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/submit",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"action": "some_action"}),
        )

        # Test without action
        activity_without_action = TaskSubmitInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="task/submit",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"name": "John"}),
        )

        # Both should match global handler
        handlers_with_action = app_with_options.router.select_handlers(activity_with_action)
        assert len(handlers_with_action) == 1
        assert handlers_with_action[0] == handle_all_submits

        handlers_without_action = app_with_options.router.select_handlers(activity_without_action)
        assert len(handlers_without_action) == 1
        assert handlers_without_action[0] == handle_all_submits

    def test_on_dialog_open_non_decorator_syntax(self, app_with_options: App) -> None:
        """Test on_dialog_open using non-decorator syntax."""

        async def handle_dialog(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Dialog opened"))

        app_with_options.on_dialog_open("my_dialog", handle_dialog)

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "my_dialog"}),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_dialog

    def test_on_dialog_submit_non_decorator_syntax(self, app_with_options: App) -> None:
        """Test on_dialog_submit using non-decorator syntax."""

        async def handle_submit(ctx: ActivityContext[TaskSubmitInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Submitted"))

        app_with_options.on_dialog_submit("my_action", handle_submit)

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = TaskSubmitInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/submit",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"action": "my_action"}),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_submit

    def test_on_dialog_open_handler_as_first_arg(self, app_with_options: App) -> None:
        """Test on_dialog_open with handler as first argument (global handler)."""

        async def handle_all(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="All"))

        app_with_options.on_dialog_open(handle_all)

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "any"}),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_all

    def test_on_dialog_submit_handler_as_first_arg(self, app_with_options: App) -> None:
        """Test on_dialog_submit with handler as first argument (global handler)."""

        async def handle_all(ctx: ActivityContext[TaskSubmitInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="All"))

        app_with_options.on_dialog_submit(handle_all)

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = TaskSubmitInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/submit",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"action": "any"}),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_all

    def test_multiple_dialog_handlers(self, app_with_options: App) -> None:
        """Test multiple dialog handlers can coexist."""

        @app_with_options.on_dialog_open("dialog_a")
        async def handle_dialog_a(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Dialog A"))

        @app_with_options.on_dialog_open("dialog_b")
        async def handle_dialog_b(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            return TaskModuleResponse(task=TaskModuleMessageResponse(value="Dialog B"))

        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity_a = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "dialog_a"}),
        )

        activity_b = TaskFetchInvokeActivity(
            id="test-activity-id-2",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "dialog_b"}),
        )

        # Verify each handler only matches its specific dialog_id
        handlers_a = app_with_options.router.select_handlers(activity_a)
        assert len(handlers_a) == 1
        assert handlers_a[0] == handle_dialog_a

        handlers_b = app_with_options.router.select_handlers(activity_b)
        assert len(handlers_b) == 1
        assert handlers_b[0] == handle_dialog_b

    def test_on_dialog_open_returns_unwrapped_response(self, app_with_options: App) -> None:
        """Test that handlers can return TaskModuleResponse directly (unwrapped from InvokeResponse)."""

        @app_with_options.on_dialog_open("test_dialog")
        async def handle_dialog(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleResponse:
            # Return unwrapped TaskModuleResponse (not InvokeResponse[TaskModuleResponse])
            card = AdaptiveCard(version="1.4", body=[])
            attachment = card_attachment(AdaptiveCardAttachment(content=card))
            return TaskModuleResponse(
                task=TaskModuleContinueResponse(value=CardTaskModuleTaskInfo(title="Test", card=attachment))
            )

        # The type system should accept this - this test verifies type compatibility
        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "test_dialog"}),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_dialog

    def test_on_dialog_open_returns_wrapped_response(self, app_with_options: App) -> None:
        """Test that handlers can also return InvokeResponse[TaskModuleResponse] (wrapped)."""

        @app_with_options.on_dialog_open("test_dialog")
        async def handle_dialog(ctx: ActivityContext[TaskFetchInvokeActivity]):
            # Return wrapped InvokeResponse[TaskModuleResponse]
            card = AdaptiveCard(version="1.4", body=[])
            attachment = card_attachment(AdaptiveCardAttachment(content=card))
            return InvokeResponse(
                body=TaskModuleResponse(
                    task=TaskModuleContinueResponse(value=CardTaskModuleTaskInfo(title="Test", card=attachment))
                )
            )

        # The type system should accept this too - verifies backward compatibility
        from_account = Account(id="user-123", name="Test User", role="user")
        recipient = Account(id="bot-456", name="Test Bot", role="bot")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = TaskFetchInvokeActivity(
            id="test-activity-id",
            type="invoke",
            name="task/fetch",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
            value=TaskModuleRequest(data={"dialog_id": "test_dialog"}),
        )

        handlers = app_with_options.router.select_handlers(activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_dialog
