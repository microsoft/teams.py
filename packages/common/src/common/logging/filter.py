"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import logging
import re


class ConsoleFilter(logging.Filter):
    def __init__(self, pattern: str = "*"):
        super().__init__()
        self.pattern = self._parse_magic_expr(pattern)

    def filter(self, record: logging.LogRecord) -> bool:
        return bool(self.pattern.match(record.name))

    @staticmethod
    def _parse_magic_expr(pattern: str) -> re.Pattern[str]:
        pattern = pattern.replace("*", ".*")
        return re.compile(f"^{pattern}$")
