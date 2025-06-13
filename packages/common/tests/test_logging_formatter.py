"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Collection, Union

from microsoft.teams.common.logging import ANSI, ConsoleFormatter


def create_record(
    name: str, level: int, msg: Union[str, dict[str, Collection[str]], list[Collection[str]]]
) -> logging.LogRecord:
    record = logging.LogRecord(name=name, level=level, pathname="test.py", lineno=1, msg=msg, args=(), exc_info=None)
    record.levelname = logging.getLevelName(level)
    return record


def test_error_formatting() -> None:
    formatter = ConsoleFormatter()
    record = create_record("test", logging.ERROR, "Error message")

    result = formatter.format(record)
    expected = (
        f"{ANSI.FOREGROUND_RED.value}{ANSI.BOLD.value}"
        + f"[ERROR] test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value} Error message"
    )
    assert result == expected


def test_warning_formatting() -> None:
    formatter = ConsoleFormatter()
    record = create_record("test", logging.WARNING, "Warning message")

    result = formatter.format(record)
    expected = (
        f"{ANSI.FOREGROUND_YELLOW.value}{ANSI.BOLD.value}[WARNING] "
        + f"test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value} Warning message"
    )
    assert result == expected


def test_info_formatting() -> None:
    formatter = ConsoleFormatter()
    record = create_record("test", logging.INFO, "Info message")

    result = formatter.format(record)
    expected = (
        f"{ANSI.FOREGROUND_CYAN.value}{ANSI.BOLD.value}[INFO] "
        + f"test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value} Info message"
    )
    assert result == expected


def test_debug_formatting() -> None:
    formatter = ConsoleFormatter()
    record = create_record("test", logging.DEBUG, "Debug message")

    result = formatter.format(record)
    expected = (
        f"{ANSI.FOREGROUND_MAGENTA.value}{ANSI.BOLD.value}"
        + f"[DEBUG] test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value} Debug message"
    )
    assert result == expected


def test_dict_message_formatting() -> None:
    formatter = ConsoleFormatter()
    dict_msg = {"key": "value", "nested": {"inner": "data"}}
    record = create_record("test", logging.INFO, dict_msg)

    result = formatter.format(record)
    result_lines = result.split("\n")

    prefix = (
        f"{ANSI.FOREGROUND_CYAN.value}{ANSI.BOLD.value}"
        + f"[INFO] test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value}"
    )
    assert result_lines[0].startswith(prefix)
    assert '"key": "value"' in result
    assert '"nested": {' in result
    assert '"inner": "data"' in result


def test_list_message_formatting() -> None:
    formatter = ConsoleFormatter()
    list_msg = ["item1", "item2", {"key": "value"}]
    record = create_record("test", logging.INFO, list_msg)

    result = formatter.format(record)
    result_lines = result.split("\n")

    prefix = (
        f"{ANSI.FOREGROUND_CYAN.value}{ANSI.BOLD.value}[INFO] test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value}"
    )
    assert result_lines[0].startswith(prefix)
    assert '"item1"' in result
    assert '"item2"' in result
    assert '"key": "value"' in result


def test_multiline_message_formatting() -> None:
    formatter = ConsoleFormatter()
    multiline_msg = "Line 1\nLine 2\nLine 3"
    record = create_record("test", logging.INFO, multiline_msg)

    result = formatter.format(record)
    expected_lines = [
        f"{ANSI.FOREGROUND_CYAN.value}{ANSI.BOLD.value}"
        + f"[INFO] test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value} Line 1",
        f"{ANSI.FOREGROUND_CYAN.value}{ANSI.BOLD.value}"
        + f"[INFO] test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value} Line 2",
        f"{ANSI.FOREGROUND_CYAN.value}{ANSI.BOLD.value}"
        + f"[INFO] test{ANSI.FOREGROUND_RESET.value}{ANSI.BOLD_RESET.value} Line 3",
    ]
    expected = "\n".join(expected_lines)
    assert result == expected


def test_unknown_level_formatting() -> None:
    formatter = ConsoleFormatter()
    record = create_record("test", 123, "Custom level message")

    result = formatter.format(record)
    assert result.endswith("Custom level message")
    assert "[LEVEL 123]" in result
    assert "test" in result
