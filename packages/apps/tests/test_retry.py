"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import MagicMock

import pytest
from microsoft.teams.apps.utils import RetryOptions, retry

# pyright: basic


class TestRetryOptions:
    """Test RetryOptions functionality."""

    def test_default_initialization(self):
        """Test that RetryOptions initializes with correct defaults."""
        options = RetryOptions()
        assert options.max_attempts == 5
        assert options.delay == 0.5
        assert options.max_delay == 30.0
        assert options.jitter_type == "full"
        assert options.attempt_number == 1
        assert options.logger is not None

    def test_custom_initialization(self):
        """Test that RetryOptions can be initialized with custom values."""
        mock_logger = MagicMock()
        options = RetryOptions(
            max_attempts=3,
            delay=1.0,
            max_delay=60.0,
            jitter_type="none",
            logger=mock_logger,
            attempt_number=2,
        )
        assert options.max_attempts == 3
        assert options.delay == 1.0
        assert options.max_delay == 60.0
        assert options.jitter_type == "none"
        assert options.attempt_number == 2
        # Logger should be a child of the provided logger
        mock_logger.getChild.assert_called_once_with("@teams/retry")


class TestRetry:
    """Test retry functionality."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test that successful operations don't retry."""
        call_count = 0

        async def success_factory():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry(success_factory)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_attempt_number_increments_correctly(self):
        """Test that attempt numbers increment correctly in log messages."""
        call_count = 0
        mock_logger = MagicMock()
        logged_messages = []

        def capture_debug(msg):
            logged_messages.append(msg)

        mock_child_logger = MagicMock()
        mock_child_logger.debug.side_effect = capture_debug
        mock_logger.getChild.return_value = mock_child_logger

        async def failing_factory():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        options = RetryOptions(max_attempts=3, delay=0.01, jitter_type="none", logger=mock_logger)
        result = await retry(failing_factory, options)

        assert result == "success"
        assert call_count == 3

        # Check that attempt numbers are logged correctly
        delay_messages = [msg for msg in logged_messages if "before retry (attempt" in msg]
        assert len(delay_messages) == 2  # Two retries (attempts 1 and 2 failed)
        assert "(attempt 1)" in delay_messages[0]  # First retry shows attempt 1 (which failed)
        assert "(attempt 2)" in delay_messages[1]  # Second retry shows attempt 2 (which failed)

    @pytest.mark.asyncio
    async def test_exponential_backoff_increases(self):
        """Test that exponential backoff delays increase exponentially."""
        call_count = 0
        mock_logger = MagicMock()
        logged_delays = []

        def capture_debug(msg):
            if "Delaying" in msg and "before retry" in msg:
                # Extract delay value from message like "Delaying 1.00s before retry..."
                delay_str = msg.split("Delaying ")[1].split("s")[0]
                logged_delays.append(float(delay_str))

        mock_child_logger = MagicMock()
        mock_child_logger.debug.side_effect = capture_debug
        mock_logger.getChild.return_value = mock_child_logger

        async def failing_factory():
            nonlocal call_count
            call_count += 1
            if call_count < 4:  # Fail first 3 attempts
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        # Use no jitter to test pure exponential backoff
        options = RetryOptions(max_attempts=4, delay=1.0, jitter_type="none", logger=mock_logger)
        result = await retry(failing_factory, options)

        assert result == "success"
        assert call_count == 4
        assert len(logged_delays) == 3  # Three retries

        # Check exponential increase: base_delay * (2^(attempt_number - 1))
        # Attempt 1: 1.0 * (2^0) = 1.0
        # Attempt 2: 1.0 * (2^1) = 2.0
        # Attempt 3: 1.0 * (2^2) = 4.0
        assert logged_delays[0] == 1.0  # First retry (after attempt 1 failed)
        assert logged_delays[1] == 2.0  # Second retry (after attempt 2 failed)
        assert logged_delays[2] == 4.0  # Third retry (after attempt 3 failed)

    @pytest.mark.asyncio
    async def test_logger_name_consistent(self):
        """Test that logger name doesn't keep growing with recursive calls."""
        call_count = 0
        mock_logger = MagicMock()
        mock_logger.name = "test_logger"

        # Track how many times getChild is called
        child_call_count = 0

        def track_get_child(child_name):
            nonlocal child_call_count
            child_call_count += 1
            child_mock = MagicMock()
            child_mock.name = f"{mock_logger.name}.{child_name}"
            return child_mock

        mock_logger.getChild.side_effect = track_get_child

        async def failing_factory():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        options = RetryOptions(max_attempts=3, delay=0.01, logger=mock_logger)
        result = await retry(failing_factory, options)

        assert result == "success"
        assert call_count == 3

        # getChild should only be called once (for the initial RetryOptions)
        # Recursive calls should reuse the existing child logger
        assert child_call_count == 1
        mock_logger.getChild.assert_called_once_with("@teams/retry")

    @pytest.mark.asyncio
    async def test_final_attempt_failure_raises(self):
        """Test that final attempt failures are raised."""
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Always fails - attempt {call_count}")

        options = RetryOptions(max_attempts=2, delay=0.01, jitter_type="none")

        with pytest.raises(ValueError, match="Always fails - attempt 2"):
            await retry(always_fail, options)

        assert call_count == 2  # Should attempt exactly max_attempts times
