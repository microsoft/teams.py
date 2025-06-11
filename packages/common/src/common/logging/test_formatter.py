"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Union

from .ansi import ANSI
from .formatter import ConsoleFormatter


def create_record(name: str, level: int, msg: Union[str, dict, list]) -> logging.LogRecord:
    record = logging.LogRecord(name=name, level=level, pathname="test.py", lineno=1, msg=msg, args=(), exc_info=None)
    record.levelname = logging.getLevelName(level)
    return record


def test_error_formatting():
    formatter = ConsoleFormatter()
    record = create_record("test", logging.ERROR, "Error message")

    result = formatter.format(record)
    expected = f"{ANSI.FOREGROUND_RED}{ANSI.BOLD}[ERROR] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET} Error message"
    assert result == expected


def test_warning_formatting():
    formatter = ConsoleFormatter()
    record = create_record("test", logging.WARNING, "Warning message")

    result = formatter.format(record)
    expected = (
        f"{ANSI.FOREGROUND_YELLOW}{ANSI.BOLD}[WARNING] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET} Warning message"
    )
    assert result == expected


def test_info_formatting():
    formatter = ConsoleFormatter()
    record = create_record("test", logging.INFO, "Info message")

    result = formatter.format(record)
    expected = f"{ANSI.FOREGROUND_CYAN}{ANSI.BOLD}[INFO] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET} Info message"
    assert result == expected


def test_debug_formatting():
    formatter = ConsoleFormatter()
    record = create_record("test", logging.DEBUG, "Debug message")

    result = formatter.format(record)
    expected = f"{ANSI.FOREGROUND_MAGENTA}{ANSI.BOLD}[DEBUG] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET} Debug message"
    assert result == expected


def test_dict_message_formatting():
    formatter = ConsoleFormatter()
    dict_msg = {"key": "value", "nested": {"inner": "data"}}
    record = create_record("test", logging.INFO, dict_msg)

    result = formatter.format(record)
    result_lines = result.split("\n")

    prefix = f"{ANSI.FOREGROUND_CYAN}{ANSI.BOLD}[INFO] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET}"
    assert result_lines[0].startswith(prefix)
    assert '"key": "value"' in result
    assert '"nested": {' in result
    assert '"inner": "data"' in result


def test_list_message_formatting():
    formatter = ConsoleFormatter()
    list_msg = ["item1", "item2", {"key": "value"}]
    record = create_record("test", logging.INFO, list_msg)

    result = formatter.format(record)
    result_lines = result.split("\n")

    prefix = f"{ANSI.FOREGROUND_CYAN}{ANSI.BOLD}[INFO] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET}"
    assert result_lines[0].startswith(prefix)
    assert '"item1"' in result
    assert '"item2"' in result
    assert '"key": "value"' in result


def test_multiline_message_formatting():
    formatter = ConsoleFormatter()
    multiline_msg = "Line 1\nLine 2\nLine 3"
    record = create_record("test", logging.INFO, multiline_msg)

    result = formatter.format(record)
    expected_lines = [
        f"{ANSI.FOREGROUND_CYAN}{ANSI.BOLD}[INFO] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET} Line 1",
        f"{ANSI.FOREGROUND_CYAN}{ANSI.BOLD}[INFO] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET} Line 2",
        f"{ANSI.FOREGROUND_CYAN}{ANSI.BOLD}[INFO] test{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET} Line 3",
    ]
    expected = "\n".join(expected_lines)
    assert result == expected


def test_unknown_level_formatting():
    formatter = ConsoleFormatter()
    record = create_record("test", 123, "Custom level message")

    result = formatter.format(record)
    assert result.endswith("Custom level message")
    assert "[LEVEL 123]" in result
    assert "test" in result
