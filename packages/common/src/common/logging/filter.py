"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import re


class ConsoleFilter(logging.Filter):
    """
    A logging filter that matches log records against a pattern.

    Attributes:
        pattern (str): The pattern to match against log record names.
    """

    def __init__(self, pattern: str = "*"):
        super().__init__()
        self.pattern = self._parse_magic_expr(pattern)

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records based on a pattern.
        Args:
            record (logging.LogRecord): The log record to filter.
        Returns:
            bool: True if the record matches the pattern, False otherwise.
        """
        return bool(self.pattern.match(record.name))

    @staticmethod
    def _parse_magic_expr(pattern: str) -> re.Pattern[str]:
        pattern = pattern.replace("*", ".*")
        return re.compile(f"^{pattern}$")
