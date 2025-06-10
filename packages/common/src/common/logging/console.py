"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, TypedDict

from .filter import ConsoleFilter
from .formatter import ConsoleFormatter


class ConsoleLoggerOptions(TypedDict, total=False):
    """
    ConsoleLoggerOptions is a dictionary that contains the options for the ConsoleLogger.

    :param level: The level of the logger (error, warn, info, debug)
    :param pattern: The pattern of the logger (e.g. "my_module.*")
    """

    level: str
    pattern: str


class ConsoleLogger:
    """
    ConsoleLogger is a class that creates a logger for the console.
    """

    _levels = {"error": logging.ERROR, "warn": logging.WARNING, "info": logging.INFO, "debug": logging.DEBUG}

    def create_logger(self, name: str, options: Optional[ConsoleLoggerOptions] = None) -> logging.Logger:
        """
        Create a logger for the console.

        :param name: The name of the logger
        :param options: The options for the logger
        """

        logger = logging.getLogger(name)
        logger.handlers = []

        handler = logging.StreamHandler()
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)

        level = (os.environ.get("LOG_LEVEL") or (options and options.get("level")) or "info").lower()
        logger.setLevel(self._levels.get(level, logging.INFO))

        pattern = os.environ.get("LOG") or (options and options.get("pattern")) or "*"
        logger.addFilter(ConsoleFilter(pattern))

        return logger
