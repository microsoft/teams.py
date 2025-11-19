"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import asyncio
from unittest.mock import Mock

import pytest
from microsoft.teams.common.events import EventEmitter


class TestEventEmitter:
    def test_on_registers_handler(self):
        emitter = EventEmitter()
        handler = Mock()

        subscription_id = emitter.on("test_event", handler)

        assert isinstance(subscription_id, int)
        assert emitter.listener_count("test_event") == 1

    def test_emit_calls_handler(self):
        emitter = EventEmitter()
        handler = Mock()

        emitter.on("test_event", handler)
        emitter.emit("test_event", "test_data")

        handler.assert_called_once_with("test_data")

    def test_emit_with_no_data(self):
        emitter = EventEmitter()
        handler = Mock()

        emitter.on("test_event", handler)
        emitter.emit("test_event")

        handler.assert_called_once_with(None)

    def test_multiple_handlers(self):
        emitter = EventEmitter()
        handler1 = Mock()
        handler2 = Mock()

        emitter.on("test_event", handler1)
        emitter.on("test_event", handler2)
        emitter.emit("test_event", "test_data")

        handler1.assert_called_once_with("test_data")
        handler2.assert_called_once_with("test_data")

    def test_off_removes_handler(self):
        emitter = EventEmitter()
        handler = Mock()

        subscription_id = emitter.on("test_event", handler)
        emitter.off(subscription_id)
        emitter.emit("test_event", "test_data")

        handler.assert_not_called()
        assert emitter.listener_count("test_event") == 0

    def test_once_handler_called_once(self):
        emitter = EventEmitter()
        handler = Mock()

        emitter.once("test_event", handler)
        emitter.emit("test_event", "data1")
        emitter.emit("test_event", "data2")

        handler.assert_called_once_with("data1")

    def test_once_returns_subscription_id(self):
        emitter = EventEmitter()
        handler = Mock()

        subscription_id = emitter.once("test_event", handler)

        assert isinstance(subscription_id, int)

    def test_emit_nonexistent_event(self):
        emitter = EventEmitter()

        # Should not raise exception
        emitter.emit("nonexistent_event", "data")

    def test_off_nonexistent_subscription(self):
        emitter = EventEmitter()

        # Should not raise exception
        emitter.off(999)

    def test_handler_exception_doesnt_break_other_handlers(self):
        emitter = EventEmitter()
        handler1 = Mock(side_effect=Exception("test error"))
        handler2 = Mock()

        emitter.on("test_event", handler1)
        emitter.on("test_event", handler2)
        emitter.emit("test_event", "test_data")

        handler1.assert_called_once_with("test_data")
        handler2.assert_called_once_with("test_data")

    def test_listener_count(self):
        emitter = EventEmitter()
        handler1 = Mock()
        handler2 = Mock()

        assert emitter.listener_count("test_event") == 0

        emitter.on("test_event", handler1)
        assert emitter.listener_count("test_event") == 1

        emitter.on("test_event", handler2)
        assert emitter.listener_count("test_event") == 2

    def test_event_names(self):
        emitter = EventEmitter()
        handler = Mock()

        assert emitter.event_names() == []

        emitter.on("event1", handler)
        emitter.on("event2", handler)

        event_names = emitter.event_names()
        assert "event1" in event_names
        assert "event2" in event_names
        assert len(event_names) == 2

    def test_remove_all_listeners_specific_event(self):
        emitter = EventEmitter()
        handler = Mock()

        emitter.on("event1", handler)
        emitter.on("event2", handler)

        emitter.remove_all_listeners("event1")

        assert emitter.listener_count("event1") == 0
        assert emitter.listener_count("event2") == 1

    def test_remove_all_listeners_all_events(self):
        emitter = EventEmitter()
        handler = Mock()

        emitter.on("event1", handler)
        emitter.on("event2", handler)

        emitter.remove_all_listeners()

        assert emitter.listener_count("event1") == 0
        assert emitter.listener_count("event2") == 0
        assert emitter.event_names() == []

    def test_emit_with_async_handler(self):
        emitter = EventEmitter()
        handler = Mock()

        async def async_handler(data):
            handler(data)

        emitter.on("test_event", async_handler)
        emitter.emit("test_event", "test_data")

        handler.assert_called_once_with("test_data")

    def test_emit_with_mixed_handlers(self):
        emitter = EventEmitter()
        sync_handler = Mock()
        async_handler = Mock()

        async def async_handler_func(data):
            async_handler(data)

        emitter.on("test_event", sync_handler)
        emitter.on("test_event", async_handler_func)

        emitter.emit("test_event", "test_data")

        sync_handler.assert_called_once_with("test_data")
        async_handler.assert_called_once_with("test_data")

    def test_emit_async_handler_exception_doesnt_break_others(self):
        emitter = EventEmitter()

        async def failing_handler(data):
            raise Exception("test error")

        is_called = False

        async def working_handler(data):
            nonlocal is_called
            is_called = True

        emitter.on("test_event", failing_handler)
        emitter.on("test_event", working_handler)

        emitter.emit("test_event", "test_data")

        assert is_called

    def test_unique_subscription_ids(self):
        emitter = EventEmitter()
        handler = Mock()

        id1 = emitter.on("event1", handler)
        id2 = emitter.on("event2", handler)
        id3 = emitter.once("event3", handler)

        assert id1 != id2 != id3
        assert len({id1, id2, id3}) == 3

    @pytest.mark.asyncio
    async def test_emit_from_async_context_with_async_handlers_works(self):
        emitter = EventEmitter()
        handler = Mock()

        async def async_handler(data):
            handler(data)

        emitter.on("test_event", async_handler)

        emitter.emit("test_event", "test_data")

        # Give async handlers a moment to complete
        await asyncio.sleep(0.01)

        handler.assert_called_once_with("test_data")

    @pytest.mark.asyncio
    async def test_emit_from_async_context_with_sync_handlers_works(self):
        emitter = EventEmitter()
        handler = Mock()

        emitter.on("test_event", handler)

        emitter.emit("test_event", "test_data")

        handler.assert_called_once_with("test_data")

    def test_off_during_iteration_safe(self):
        emitter = EventEmitter()
        handler1 = Mock()
        handler2 = Mock()

        # Register handlers for multiple events
        id1 = emitter.on("event1", handler1)
        _id2 = emitter.on("event2", handler2)

        emitter.off(id1)

        # Verify event1 is completely removed, event2 still exists
        assert emitter.listener_count("event1") == 0
        assert emitter.listener_count("event2") == 1
        assert "event1" not in emitter.event_names()
        assert "event2" in emitter.event_names()
