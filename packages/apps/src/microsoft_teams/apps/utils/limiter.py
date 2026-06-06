"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from time import monotonic
from typing import Awaitable, Callable


def make_limiter(rate: int, period: float = 1.0) -> Callable[[], Awaitable[None]]:
    """Leaky-slot limiter: at most `rate` acquisitions per `period` seconds.

    The slot is reserved (read then write of `next_slot`) with no await in
    between, so reservations are race-free under single-threaded asyncio. The
    first call never waits.
    """
    if rate < 1:
        raise ValueError("rate must be >= 1")
    if period < 0:
        raise ValueError("period must be >= 0")

    interval = period / rate
    next_slot = monotonic()

    async def acquire() -> None:
        nonlocal next_slot
        now = monotonic()
        slot = max(now, next_slot)
        next_slot = slot + interval
        wait = slot - now
        if wait > 0:
            await asyncio.sleep(wait)

    return acquire
