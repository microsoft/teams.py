"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from logging import Logger
from typing import Awaitable, Callable, Optional, TypeVar

from microsoft.teams.common.logging import ConsoleLogger

T = TypeVar("T")


class RetryOptions:
    def __init__(
        self,
        max_attempts: int = 5,
        delay: float = 0.5,  # in seconds
        logger: Optional[Logger] = None,
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.logger = logger or ConsoleLogger().create_logger("@teams/http-stream")


async def retry(factory: Callable[[], "Awaitable[T]"], options: Optional[RetryOptions] = None) -> T:
    options = options or RetryOptions()
    max_attempts = options.max_attempts
    delay = options.delay
    logger = options.logger

    try:
        return await factory()
    except Exception as err:
        if max_attempts > 1:
            logger.debug(f"Delaying {delay:.2f}s before retry...")
            await asyncio.sleep(delay)
            logger.debug("Retrying...")
            return await retry(
                factory,
                RetryOptions(
                    max_attempts=max_attempts - 1,
                    delay=delay * 2,  # exponential backoff
                    logger=logger,
                ),
            )
        logger.error("Final attempt failed.", exc_info=err)
        raise
