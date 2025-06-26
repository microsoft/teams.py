"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest


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
