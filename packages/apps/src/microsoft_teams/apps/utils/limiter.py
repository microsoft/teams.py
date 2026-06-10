"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from time import monotonic
from typing import Awaitable, Callable


def make_limiter(interval: float) -> Callable[[], Awaitable[None]]:
    """Fixed-interval gate (a token bucket of size 1): consecutive
    acquisitions are spaced at least `interval` seconds apart.

    The slot is reserved (read then write of `next_slot`) with no await in
    between, so reservations are race-free under single-threaded asyncio. The
    first call never waits, and `interval=0` disables pacing.
    """
    if interval < 0:
        raise ValueError("interval must be >= 0")

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
