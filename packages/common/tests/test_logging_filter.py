"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from unittest.mock import MagicMock

from microsoft.teams.common.logging import ConsoleFilter


def test_default_pattern() -> None:
    filter = ConsoleFilter()
    record = MagicMock(spec=logging.LogRecord)
    record.name = "test"

    assert filter.filter(record) is True


def test_exact_match() -> None:
    filter = ConsoleFilter("test")
    record = MagicMock(spec=logging.LogRecord)
    record.name = "test"

    assert filter.filter(record) is True


def test_wildcard_prefix() -> None:
    filter = ConsoleFilter("test*")

    matching_record = MagicMock(spec=logging.LogRecord)
    matching_record.name = "testLogger"
    assert filter.filter(matching_record) is True

    non_matching_record = MagicMock(spec=logging.LogRecord)
    non_matching_record.name = "logger"
    assert filter.filter(non_matching_record) is False


def test_wildcard_suffix() -> None:
    filter = ConsoleFilter("*test")

    matching_record = MagicMock(spec=logging.LogRecord)
    matching_record.name = "mytest"
    assert filter.filter(matching_record) is True

    non_matching_record = MagicMock(spec=logging.LogRecord)
    non_matching_record.name = "tester"
    assert filter.filter(non_matching_record) is False


def test_wildcard_middle() -> None:
    filter = ConsoleFilter("my*test")

    matching_record = MagicMock(spec=logging.LogRecord)
    matching_record.name = "myloggertest"
    assert filter.filter(matching_record) is True

    non_matching_record = MagicMock(spec=logging.LogRecord)
    non_matching_record.name = "mylogger"
    assert filter.filter(non_matching_record) is False


def test_multiple_wildcards() -> None:
    filter = ConsoleFilter("my*log*test")

    matching_record = MagicMock(spec=logging.LogRecord)
    matching_record.name = "myapplicationloggertest"
    assert filter.filter(matching_record) is True

    partial_match_record = MagicMock(spec=logging.LogRecord)
    partial_match_record.name = "mylogger"
    assert filter.filter(partial_match_record) is False


def test_case_sensitivity() -> None:
    filter = ConsoleFilter("Test")

    upper_record = MagicMock(spec=logging.LogRecord)
    upper_record.name = "Test"
    assert filter.filter(upper_record) is True

    lower_record = MagicMock(spec=logging.LogRecord)
    lower_record.name = "test"
    assert filter.filter(lower_record) is False
