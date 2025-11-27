"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging

from .ansi import ANSI


class ConsoleFormatter(logging.Formatter):
    """
    A custom logging formatter that formats log messages with colors and prefixes.
    """

    _colors = {
        "ERROR": ANSI.FOREGROUND_RED,
        "WARNING": ANSI.FOREGROUND_YELLOW,
        "INFO": ANSI.FOREGROUND_CYAN,
        "DEBUG": ANSI.FOREGROUND_MAGENTA,
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with colors and prefixes.
        Args:
            record (logging.LogRecord): The log record to format.
        Returns:
            str: The formatted log message.
        """
        if isinstance(record.msg, (dict, list)):
            record.msg = json.dumps(record.msg, indent=2)  # pyright: ignore[reportUnknownMemberType]

        level_name = record.levelname.upper()
        color = self._colors.get(level_name, ANSI.FOREGROUND_CYAN)
        prefix = f"{color.value}{ANSI.BOLD.value}[{level_name}]"
        name = f"{record.name}{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value}"

        message = record.getMessage()
        lines = message.split("\n")
        formatted_lines = [f"{prefix} {name} {line}" for line in lines]
        return "\n".join(formatted_lines)
