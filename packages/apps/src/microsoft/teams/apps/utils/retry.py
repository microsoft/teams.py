"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import random
from logging import Logger
from typing import Awaitable, Callable, Literal, Optional, TypeVar

from microsoft.teams.common import ConsoleLogger

T = TypeVar("T")

# Type alias for jitter types using string literals
JitterType = Literal["none", "full", "equal", "decorrelated"]


class RetryOptions:
    def __init__(
        self,
        max_attempts: int = 5,
        delay: float = 0.5,  # in seconds
        max_delay: float = 30.0,  # maximum delay cap
        jitter_type: JitterType = "full",
        logger: Optional[Logger] = None,
        previous_delay: Optional[float] = None,  # Internal use for decorrelated jitter
        attempt_number: int = 1,  # Internal use to track current attempt number
        _internal_logger: Optional[Logger] = None,  # Internal use to pass existing child logger
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.max_delay = max_delay
        self.jitter_type: JitterType = jitter_type
        # Use existing internal logger if provided, otherwise create child logger
        self.logger = (
            _internal_logger
            if _internal_logger
            else (logger.getChild("@teams/retry") if logger else ConsoleLogger().create_logger("@teams/retry"))
        )
        self.previous_delay = previous_delay
        self.attempt_number = attempt_number


def _apply_jitter(delay: float, jitter_type: JitterType, previous_delay: Optional[float] = None) -> float:
    """Apply jitter to the delay to prevent thundering herd problems."""
    if jitter_type == "none":
        return delay
    elif jitter_type == "full":
        # Random delay between 0 and the computed delay
        return random.uniform(0, delay)
    elif jitter_type == "equal":
        # Random delay between half the computed delay and the full computed delay
        return random.uniform(delay / 2, delay)
    elif jitter_type == "decorrelated":
        # Decorrelated jitter: random delay between base delay and 3 * previous delay
        base_delay = delay / 4  # Start with a smaller base
        if previous_delay is None:
            previous_delay = base_delay
        return random.uniform(base_delay, min(delay, 3 * previous_delay))
    else:
        return delay


async def retry(factory: Callable[[], Awaitable[T]], options: Optional[RetryOptions] = None) -> T:
    options = options or RetryOptions()
    max_attempts = options.max_attempts
    base_delay = options.delay
    max_delay = options.max_delay
    jitter_type: JitterType = options.jitter_type
    logger = options.logger
    previous_delay = options.previous_delay
    attempt_number = options.attempt_number

    try:
        return await factory()
    except (asyncio.CancelledError, KeyboardInterrupt):
        # Don't retry cancellation or keyboard interrupts
        logger.debug("Operation cancelled or interrupted, not retrying")
        raise
    except Exception as err:
        if max_attempts > 1:
            # Calculate exponential backoff delay using the attempt number
            exponential_delay = base_delay * (2 ** (attempt_number - 1))

            # Cap the delay at max_delay
            capped_delay = min(exponential_delay, max_delay)

            # Apply jitter
            jittered_delay = _apply_jitter(capped_delay, jitter_type, previous_delay)

            logger.debug(f"Delaying {jittered_delay:.2f}s before retry (attempt {attempt_number})...")
            await asyncio.sleep(jittered_delay)
            logger.debug("Retrying...")

            return await retry(
                factory,
                RetryOptions(
                    max_attempts=max_attempts - 1,
                    delay=base_delay,
                    max_delay=max_delay,
                    jitter_type=jitter_type,
                    previous_delay=jittered_delay,  # Pass current delay for decorrelated jitter
                    attempt_number=attempt_number + 1,  # Increment attempt number
                    _internal_logger=logger,  # Pass the existing logger to avoid nested children
                ),
            )
        logger.error("Final attempt failed.", exc_info=err)
        raise
