"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
from time import monotonic
from unittest.mock import MagicMock, patch

import pytest
from httpx import HTTPStatusError, Request, Response
from microsoft_teams.api import (
    Account,
    ApiClient,
    CardAction,
    CardActionType,
    ConversationAccount,
    ConversationReference,
    MessageActivityInput,
    SentActivity,
    SuggestedActions,
    TypingActivityInput,
)
from microsoft_teams.apps import HttpStream
from microsoft_teams.apps.plugins import StreamCancelledError


class TestHttpStream:
    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_api_client(self):
        client = MagicMock(spec=ApiClient)

        mock_activities = MagicMock()
        mock_conversations = MagicMock()
        mock_conversations.activities.return_value = mock_activities
        client.conversations = mock_conversations

        client.send_call_count = 0
        client.sent_activities = []

        async def mock_send(activity):
            client.send_call_count += 1
            client.sent_activities.append(activity)
            return SentActivity(id=f"activity-{client.send_call_count}", activity_params=activity)

        client.conversations.activities().create = mock_send

        return client

    @pytest.fixture
    def conversation_reference(self):
        return ConversationReference(
            service_url="https://smba.trafficmanager.net/teams/",
            bot=Account(id="test-bot", name="Test Bot"),
            conversation=ConversationAccount(id="test-conversation", conversation_type="personal"),
            activity_id="test-activity",
            channel_id="msteams",
        )

    @pytest.fixture
    def http_stream(self, mock_api_client, conversation_reference):
        return HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

    @pytest.fixture
    def patch_loop_call_later(self):
        """Patch the event loop call_later to store scheduled callbacks."""
        scheduled = []

        def _patch(loop):
            def mock_call_later(delay, callback, *args):
                scheduled.append((callback, args))
                return MagicMock()  # fake TimerHandle

            return patch.object(loop, "call_later", side_effect=mock_call_later), scheduled

        return _patch

    async def _run_scheduled_flushes(self, scheduled):
        """Helper to run all scheduled flush callbacks asynchronously."""
        while scheduled:
            callback, args = scheduled.pop(0)
            callback(*args)
            await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_stream_multiple_emits_with_timer(self, http_stream, patch_loop_call_later):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:
            for i in range(12):
                http_stream.emit(f"Message {i + 1}")

            await asyncio.sleep(0)
            # First flush drains the entire queue, no second flush needed
            assert http_stream._client.send_call_count == 1
            assert len(scheduled) == 0

    @pytest.mark.asyncio
    async def test_stream_error_handled_gracefully(
        self, mock_api_client, conversation_reference, patch_loop_call_later
    ):
        call_count = 0
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:

            async def mock_send_with_timeout(activity):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise TimeoutError("Operation timed out")
                return SentActivity(id=f"success-after-timeout-{call_count}", activity_params=activity)

            mock_api_client.conversations.activities().create = mock_send_with_timeout
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

            stream.emit("Test message with timeout")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)
            assert call_count == 2

            result = await stream.close()
            assert result is not None

    @pytest.mark.asyncio
    async def test_stream_all_timeouts_fail_handled_gracefully(
        self, mock_api_client, conversation_reference, patch_loop_call_later
    ):
        call_count = 0
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:

            async def mock_send_all_timeout(activity):
                nonlocal call_count
                call_count += 1
                raise TimeoutError("All operations timed out")

            mock_api_client.conversations.activities().create = mock_send_all_timeout
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

            stream.emit("Test message with all timeouts")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)
            assert call_count == 8
            await stream.close()

    @pytest.mark.asyncio
    async def test_stream_update_status_sends_typing_activity(
        self, mock_api_client, conversation_reference, patch_loop_call_later
    ):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)
            stream.update("Thinking...")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert len(mock_api_client.sent_activities) > 0
            activity = mock_api_client.sent_activities[0]
            assert isinstance(activity, TypingActivityInput)
            assert activity.text == "Thinking..."
            assert activity.channel_data is not None
            assert activity.channel_data.stream_type == "informative"
            assert stream.sequence >= 2

    @pytest.mark.asyncio
    async def test_stream_sequence_of_update_and_emit(
        self, mock_api_client, conversation_reference, patch_loop_call_later
    ):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0.01)
            stream.update("Preparing response...")
            stream.emit("Final response message")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert len(mock_api_client.sent_activities) >= 2
            typing_activity = mock_api_client.sent_activities[0]
            message_activity = mock_api_client.sent_activities[1]

            assert isinstance(typing_activity, TypingActivityInput)
            assert typing_activity.text == "Preparing response..."
            assert message_activity.text == "Final response message"
            assert stream.sequence >= 3

    @pytest.mark.asyncio
    async def test_stream_concurrent_emits_do_not_flush_simultaneously(
        self, mock_api_client, conversation_reference, patch_loop_call_later
    ):
        concurrent_entries = 0
        max_concurrent_entries = 0
        lock = asyncio.Lock()
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)

        async def mock_send(activity):
            nonlocal concurrent_entries, max_concurrent_entries
            async with lock:
                concurrent_entries += 1
                max_concurrent_entries = max(max_concurrent_entries, concurrent_entries)
            await asyncio.sleep(0)
            async with lock:
                concurrent_entries -= 1
            return activity

        mock_api_client.conversations.activities().create = mock_send

        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

            async def emit_task():
                stream.emit("Concurrent message")

            tasks = [asyncio.create_task(emit_task()) for _ in range(10)]
            await asyncio.gather(*tasks)
            await self._run_scheduled_flushes(scheduled)

            assert max_concurrent_entries == 1

    @pytest.mark.asyncio
    async def test_stream_canceled_on_403(self, mock_api_client, conversation_reference, patch_loop_call_later):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:

            async def mock_send_403(activity):
                raise HTTPStatusError(
                    "Forbidden",
                    request=Request("POST", "https://example.com"),
                    response=Response(403),
                )

            mock_api_client.conversations.activities().create = mock_send_403
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

            stream.emit("Test message")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert stream.canceled is True

    @pytest.mark.asyncio
    async def test_emit_blocked_after_cancel(self, mock_api_client, conversation_reference, patch_loop_call_later):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:

            async def mock_send_403(activity):
                raise HTTPStatusError(
                    "Forbidden",
                    request=Request("POST", "https://example.com"),
                    response=Response(403),
                )

            mock_api_client.conversations.activities().create = mock_send_403
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

            stream.emit("First message")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert stream.canceled is True

            # Emit after cancel should raise
            with pytest.raises(StreamCancelledError, match="Stream has been cancelled."):
                stream.emit("Should be ignored")

    @pytest.mark.asyncio
    async def test_send_blocked_after_cancel(self, mock_api_client, conversation_reference):
        stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)
        stream._canceled = True

        with pytest.raises(StreamCancelledError, match="Teams channel stopped the stream."):
            await stream._send(TypingActivityInput(text="test"))

    @pytest.mark.asyncio
    async def test_stream_canceled_after_successful_message(
        self, mock_api_client, conversation_reference, patch_loop_call_later
    ):
        call_count = 0
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:

            async def mock_send_then_403(activity):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return SentActivity(id="activity-1", activity_params=activity)
                raise HTTPStatusError(
                    "Forbidden",
                    request=Request("POST", "https://example.com"),
                    response=Response(403),
                )

            mock_api_client.conversations.activities().create = mock_send_then_403
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0.01)

            # First emit succeeds
            stream.emit("First message")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert stream.canceled is False
            assert call_count == 1

            # Second emit triggers 403
            stream.emit("Second message")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert stream.canceled is True
            assert call_count == 2

            # Further emits raise
            with pytest.raises(StreamCancelledError, match="Stream has been cancelled."):
                stream.emit("Should be ignored")

    @pytest.mark.asyncio
    async def test_close_returns_none_when_canceled(self, mock_api_client, conversation_reference):
        stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)
        stream._canceled = True

        result = await stream.close()
        assert result is None

    @pytest.mark.asyncio
    async def test_final_activity_last_wins(self, mock_api_client, conversation_reference, patch_loop_call_later):
        """When multiple MessageActivityInputs are emitted, the last one's non-text fields are used."""
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)

        update_call_count = 0
        original_create = mock_api_client.conversations.activities().create

        async def mock_send(activity):
            nonlocal update_call_count
            if (
                hasattr(activity, "id")
                and activity.id
                and not any(e.type == "streaminfo" for e in (activity.entities or []))
            ):
                update_call_count += 1
                return SentActivity(id=activity.id, activity_params=activity)
            return await original_create(activity)

        mock_api_client.conversations.activities().create = mock_send
        mock_api_client.conversations.activities().update = mock_send

        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

            early_actions = SuggestedActions(
                to=[],
                actions=[CardAction(type=CardActionType.IM_BACK, title="Early", value="early")],
            )
            late_actions = SuggestedActions(
                to=[],
                actions=[CardAction(type=CardActionType.IM_BACK, title="Late", value="late")],
            )

            stream.emit("Hello ")
            stream.emit(MessageActivityInput(text="world").with_suggested_actions(early_actions))
            stream.emit(MessageActivityInput().add_ai_generated().with_suggested_actions(late_actions))
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            result = await stream.close()
            assert result is not None
            # The final activity should use the last emitted MessageActivityInput's suggested actions
            assert result.activity_params.suggested_actions == late_actions
            # Text should be accumulated from all emits
            assert result.activity_params.text == "Hello world"

    @pytest.mark.asyncio
    async def test_suggested_actions_on_final_message(
        self, mock_api_client, conversation_reference, patch_loop_call_later
    ):
        """Suggested actions emitted mid-stream appear on the final close() message."""
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)

        update_call_count = 0
        original_create = mock_api_client.conversations.activities().create

        async def mock_send(activity):
            nonlocal update_call_count
            if (
                hasattr(activity, "id")
                and activity.id
                and not any(e.type == "streaminfo" for e in (activity.entities or []))
            ):
                update_call_count += 1
                return SentActivity(id=activity.id, activity_params=activity)
            return await original_create(activity)

        mock_api_client.conversations.activities().create = mock_send
        mock_api_client.conversations.activities().update = mock_send

        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

            actions = SuggestedActions(
                to=[],
                actions=[
                    CardAction(type=CardActionType.IM_BACK, title="Option A", value="a"),
                    CardAction(type=CardActionType.IM_BACK, title="Option B", value="b"),
                ],
            )

            stream.emit("Streaming content...")
            stream.emit(MessageActivityInput().with_suggested_actions(actions))
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            result = await stream.close()
            assert result is not None
            assert result.activity_params.suggested_actions is not None
            assert len(result.activity_params.suggested_actions.actions) == 2
            assert result.activity_params.suggested_actions.actions[0].title == "Option A"

    @pytest.mark.asyncio
    async def test_close_waits_for_flush_to_complete(self, mock_api_client, conversation_reference):
        """close() must not send the final message while a flush is still mid-await."""
        stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0)

        # Simulate a flush in progress: lock held, _id assigned, text accumulated.
        # This mirrors the window after the inner queue drain but before SendActivity awaits resolve.
        await stream._lock.acquire()
        stream._id = "activity-1"
        stream._text = "Response text"

        close_task = asyncio.create_task(stream.close())

        # Give close() a chance to enter its wait loop, then confirm it has not sent the final message yet.
        await asyncio.sleep(0.05)
        assert mock_api_client.send_call_count == 0
        assert not close_task.done()

        # Release the lock and signal — close() should now proceed.
        stream._lock.release()
        stream._state_changed.set()

        result = await close_task
        assert result is not None
        assert mock_api_client.send_call_count == 1
        assert mock_api_client.sent_activities[0].text == "Response text"

    @pytest.mark.asyncio
    async def test_rapid_updates_are_paced_not_dropped_when_coalesce_off(self, mock_api_client, conversation_reference):
        interval = 0.05
        send_times: list[float] = []

        async def mock_send(activity):
            send_times.append(monotonic())
            mock_api_client.send_call_count += 1
            mock_api_client.sent_activities.append(activity)
            return SentActivity(id=f"activity-{mock_api_client.send_call_count}", activity_params=activity)

        mock_api_client.conversations.activities().create = mock_send

        stream = HttpStream(
            mock_api_client,
            conversation_reference,
            min_send_interval=interval,
            coalesce_informative_updates=False,
        )
        for i in range(8):
            stream.update(f"progress {i}")

        task = stream._pending
        assert task is not None
        await task

        texts = [a.text for a in mock_api_client.sent_activities]
        assert texts == [f"progress {i}" for i in range(8)]  # all sent, in order, none dropped
        gaps = [b - a for a, b in zip(send_times, send_times[1:], strict=False)]
        assert min(gaps) >= interval * 0.9  # each subsequent send waited ~one interval

    @pytest.mark.asyncio
    @pytest.mark.parametrize("interval", [0.05, 0.15])
    async def test_consecutive_emits_are_paced_across_flushes(self, mock_api_client, conversation_reference, interval):
        send_times: list[float] = []

        async def mock_send(activity):
            send_times.append(monotonic())
            mock_api_client.send_call_count += 1
            mock_api_client.sent_activities.append(activity)
            return SentActivity(id=f"activity-{mock_api_client.send_call_count}", activity_params=activity)

        mock_api_client.conversations.activities().create = mock_send

        stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=interval)
        # Each update drains its own flush, so pacing must hold across flushes (bug 2).
        for i in range(3):
            stream.update(f"step {i}")
            task = stream._pending
            assert task is not None
            await task

        texts = [a.text for a in mock_api_client.sent_activities]
        assert texts == ["step 0", "step 1", "step 2"]
        gaps = [b - a for a, b in zip(send_times, send_times[1:], strict=False)]
        assert min(gaps) >= interval * 0.9

    @pytest.mark.asyncio
    async def test_coalesce_drops_intermediate_informative_in_burst_by_default(
        self, mock_api_client, conversation_reference
    ):
        # Coalescing is the default, so a burst must not be paced one-by-one.
        stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=0.05)
        for i in range(8):
            stream.update(f"progress {i}")

        task = stream._pending
        assert task is not None
        await task

        # A burst collapses to the latest informative bubble.
        assert mock_api_client.send_call_count == 1
        assert mock_api_client.sent_activities[0].text == "progress 7"

    @pytest.mark.asyncio
    async def test_coalesce_does_not_drop_text(self, mock_api_client, conversation_reference, patch_loop_call_later):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:
            stream = HttpStream(
                mock_api_client,
                conversation_reference,
                min_send_interval=0.01,
                coalesce_informative_updates=True,
            )
            stream.update("Thinking...")
            stream.emit("The answer")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            texts = [a.text for a in mock_api_client.sent_activities]
            assert texts == ["Thinking...", "The answer"]  # informative + text both sent

    @pytest.mark.asyncio
    async def test_close_final_send_is_paced(self, mock_api_client, conversation_reference):
        # The final close() send goes through the limiter too, so it can't land
        # right behind the last chunk and trip the throttle.
        interval = 0.05
        send_times: list[float] = []

        async def mock_send(activity):
            send_times.append(monotonic())
            mock_api_client.send_call_count += 1
            mock_api_client.sent_activities.append(activity)
            return SentActivity(id=f"activity-{mock_api_client.send_call_count}", activity_params=activity)

        mock_api_client.conversations.activities().create = mock_send
        mock_api_client.conversations.activities().update = mock_send

        stream = HttpStream(mock_api_client, conversation_reference, min_send_interval=interval)
        stream.emit("chunk")
        task = stream._pending
        assert task is not None
        await task
        await stream.close()

        assert len(send_times) == 2  # chunk + final
        assert send_times[1] - send_times[0] >= interval * 0.9
