"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.devtools.devtools_plugin import DevToolsPlugin

# pyright: basic


class TestDevToolsPluginEnvironmentGuard:
    """Test that DevTools refuses to start in production environments."""

    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch):
        """Clear environment variables before each test."""
        monkeypatch.delenv("PYTHON_ENV", raising=False)
        monkeypatch.delenv("NODE_ENV", raising=False)

    @pytest.mark.asyncio
    async def test_raises_when_python_env_is_production(self, monkeypatch):
        monkeypatch.setenv("PYTHON_ENV", "production")
        plugin = DevToolsPlugin()

        with pytest.raises(RuntimeError, match="cannot be used in production"):
            await plugin.on_init()

    @pytest.mark.asyncio
    async def test_raises_when_node_env_is_production(self, monkeypatch):
        monkeypatch.setenv("NODE_ENV", "production")
        plugin = DevToolsPlugin()

        with pytest.raises(RuntimeError, match="cannot be used in production"):
            await plugin.on_init()

    @pytest.mark.asyncio
    async def test_does_not_raise_in_development(self, monkeypatch):
        monkeypatch.setenv("NODE_ENV", "development")
        plugin = DevToolsPlugin()

        # Should not raise — just logs a warning
        await plugin.on_init()

    @pytest.mark.asyncio
    async def test_does_not_raise_when_env_not_set(self):
        plugin = DevToolsPlugin()

        # Should not raise when no env var is set
        await plugin.on_init()


class TestDevToolsPluginInit:
    """Test DevToolsPlugin initialization and properties."""

    def test_init_defaults(self):
        plugin = DevToolsPlugin()
        assert plugin.pages == []
        assert plugin.sockets == {}
        assert plugin.pending == {}
        assert plugin.on_ready_callback is None
        assert plugin.on_stopped_callback is None

    def test_callback_setters(self):
        plugin = DevToolsPlugin()

        async def ready():
            pass

        async def stopped():
            pass

        plugin.on_ready_callback = ready
        plugin.on_stopped_callback = stopped
        assert plugin.on_ready_callback is ready
        assert plugin.on_stopped_callback is stopped

    def test_add_page(self):
        from microsoft_teams.devtools.page import Page

        plugin = DevToolsPlugin()
        page = Page(name="test", display_name="Test Page", url="/test")
        plugin.add_page(page)
        assert len(plugin.pages) == 1
        assert plugin.pages[0].name == "test"
