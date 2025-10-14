"""
Tests for AppConfig integration with the App class.
"""

import os

import pytest

from microsoft.teams.apps import App, AppConfig, CredentialsConfig, EndpointConfig, NetworkConfig


class TestAppConfigIntegration:
    """Tests for AppConfig integration with App."""

    def test_app_uses_custom_port_from_config(self):
        """Test that App uses custom port from AppConfig."""
        config = AppConfig(
            network=NetworkConfig(default_port=9999)
        )
        
        app = App(config=config)
        
        # Port should be set when app.start() is called, but we can verify config is stored
        assert app.config.network.default_port == 9999

    def test_app_uses_custom_endpoints_from_config(self):
        """Test that App uses custom endpoints from AppConfig."""
        config = AppConfig(
            endpoints=EndpointConfig(
                bot_api_base_url="https://custom.api.example.com",
                activity_path="/custom/activity",
                health_check_path="/custom/health",
            )
        )
        
        app = App(config=config)
        
        # Verify App uses the custom endpoint
        assert app.api.service_url == "https://custom.api.example.com"
        assert app.config.endpoints.activity_path == "/custom/activity"
        assert app.config.endpoints.health_check_path == "/custom/health"

    def test_app_uses_credentials_from_config(self):
        """Test that App uses credentials from AppConfig."""
        config = AppConfig(
            credentials=CredentialsConfig(
                client_id="test-client-id",
                client_secret="test-client-secret",
                tenant_id="test-tenant-id",
            )
        )
        
        app = App(config=config)
        
        # Verify credentials are used
        assert app.credentials is not None
        assert app.credentials.client_id == "test-client-id"
        assert app.credentials.tenant_id == "test-tenant-id"

    def test_app_validates_conflicting_credentials(self):
        """Test that App raises error for conflicting credentials."""
        config = AppConfig(
            credentials=CredentialsConfig(
                client_id="config-client-id",
            )
        )
        
        with pytest.raises(ValueError, match="Conflicting client_id"):
            App(
                client_id="options-client-id",
                client_secret="secret",
                config=config,
            )

    def test_app_options_credentials_work_without_config(self):
        """Test that AppOptions credentials still work without AppConfig."""
        app = App(
            client_id="options-client-id",
            client_secret="options-client-secret",
            tenant_id="options-tenant-id",
        )
        
        assert app.credentials is not None
        assert app.credentials.client_id == "options-client-id"
        assert app.credentials.tenant_id == "options-tenant-id"

    def test_app_uses_default_config_when_none_provided(self):
        """Test that App creates default AppConfig when none is provided."""
        app = App()
        
        # Should have default config
        assert app.config is not None
        assert app.config.network.default_port == 3978
        assert app.config.endpoints.bot_api_base_url == "https://smba.trafficmanager.net/teams"
        assert app.config.endpoints.activity_path == "/api/messages"

    def test_config_env_vars_used_by_app(self, monkeypatch):
        """Test that App respects environment variables via AppConfig."""
        monkeypatch.setenv("PORT", "7777")
        monkeypatch.setenv("BOT_API_BASE_URL", "https://env.api.example.com")
        
        app = App()
        
        # Config should use env vars
        assert app.config.network.default_port == 7777
        assert app.config.endpoints.bot_api_base_url == "https://env.api.example.com"
        assert app.api.service_url == "https://env.api.example.com"

    def test_explicit_config_overrides_env_vars(self, monkeypatch):
        """Test that explicit AppConfig values override environment variables."""
        monkeypatch.setenv("PORT", "7777")
        
        config = AppConfig(
            network=NetworkConfig(default_port=8888)
        )
        
        app = App(config=config)
        
        # Explicit config should override env var
        assert app.config.network.default_port == 8888

    def test_credentials_from_options_when_config_credentials_not_set(self):
        """Test that App uses AppOptions credentials when AppConfig.credentials is None."""
        config = AppConfig()  # No credentials in config
        
        app = App(
            client_id="options-client-id",
            client_secret="options-client-secret",
            config=config,
        )
        
        assert app.credentials is not None
        assert app.credentials.client_id == "options-client-id"

    def test_http_plugin_uses_config_endpoints(self):
        """Test that HttpPlugin uses config endpoints."""
        config = AppConfig(
            endpoints=EndpointConfig(
                activity_path="/custom/messages",
                health_check_path="/custom/status",
            )
        )
        
        app = App(config=config)
        
        # Verify HttpPlugin got the config
        assert app.http.config.endpoints.activity_path == "/custom/messages"
        assert app.http.config.endpoints.health_check_path == "/custom/status"
