"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

import pytest
from microsoft_teams.api import (
    Account,
    ConversationResource,
    MessageActivityInput,
)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test."""
    import os

    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests to ensure DEBUG logs are captured."""
    # Set the microsoft_teams logger to DEBUG level so caplog can capture DEBUG logs
    logger = logging.getLogger("microsoft_teams")
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    yield
    # Restore original level after test
    logger.setLevel(original_level)


@pytest.fixture
def mock_account():
    """Create a mock account for testing."""
    return Account(
        id="mock_account_id",
        name="Mock Account",
        aad_object_id="mock_aad_object_id",
    )


@pytest.fixture
def mock_activity():
    """Create a mock activity for testing."""
    account = Account(id="sender_id", name="Sender")
    return MessageActivityInput(type="message", text="Mock activity text", from_=account, id="test-id")


@pytest.fixture
def mock_conversation_resource():
    """Create a mock conversation resource with activity and service_url for testing."""
    return ConversationResource(
        id="mock_conversation_id",
        activity_id="mock_activity_id",
        service_url="https://mock.service.url",
    )


@pytest.fixture
def mock_conversation_resource_without_activity():
    """Create a mock conversation resource without activity for testing."""
    return ConversationResource(
        id="mock_conversation_id",
        activity_id=None,
        service_url="https://mock.service.url",
    )


@pytest.fixture
def mock_conversation_resource_minimal():
    """Create a minimal mock conversation resource with only required fields."""
    return ConversationResource(
        id="mock_conversation_id",
        activity_id=None,
        service_url=None,
    )
