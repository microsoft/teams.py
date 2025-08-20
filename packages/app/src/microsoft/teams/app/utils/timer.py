"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from typing import Awaitable, Callable, Optional, Union

TimerCallback = Union[Callable[[], None], Callable[[], Awaitable[None]]]


class Timeout:
    def __init__(self, delay: float, callback: TimerCallback) -> None:
        """
        Schedule a callback after a delay.

        Args:
            delay: Delay in seconds before callback is executed.
            callback: Function to run after delay.
        """
        self._delay: float = delay
        self._callback: TimerCallback = callback
        self._handle: Optional[asyncio.TimerHandle] = None
        self._cancelled: bool = False

        loop = asyncio.get_event_loop()
        self._handle = loop.call_later(delay, self._run)

    def _run(self) -> None:
        if self._cancelled:
            return

        if asyncio.iscoroutinefunction(self._callback):
            asyncio.create_task(self._callback())  # Fire-and-forget
        else:
            self._callback()

    def cancel(self) -> None:
        """
        Cancel the timeout before it triggers.
        """
        if self._handle is not None:
            self._handle.cancel()
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        """Check if the timeout was cancelled."""
        return self._cancelled
