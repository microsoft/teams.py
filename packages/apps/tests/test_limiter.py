"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from time import monotonic

import pytest
from microsoft_teams.apps.utils import make_limiter


@pytest.mark.asyncio
async def test_make_limiter_spaces_calls():
    acquire = make_limiter(0.05)

    start = monotonic()
    await acquire()  # first call returns immediately
    first_done = monotonic()
    await acquire()
    await acquire()
    elapsed = monotonic() - start

    assert first_done - start < 0.05  # leading edge is not delayed
    assert elapsed >= 0.10  # two subsequent calls each waited one interval


@pytest.mark.parametrize("interval", [-0.5, -1])
def test_make_limiter_rejects_negative_interval(interval: float):
    with pytest.raises(ValueError):
        make_limiter(interval)
