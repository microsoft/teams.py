"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for the AppConfig and related configuration classes.
"""

import pytest

from microsoft.teams.apps.config import (
    AppConfig,
    AuthConfig,
    EndpointConfig,
    LoggerConfig,
    NetworkConfig,
    PluginConfig,
    RetryConfig,
    SignInConfig,
)


class TestNetworkConfig:
    """Tests for NetworkConfig."""

    def test_default_values(self):
        """Test that NetworkConfig has correct default values."""
        config = NetworkConfig()
        assert config.default_port == 3978
        assert config.host == "0.0.0.0"
        assert config.user_agent is None
        assert config.uvicorn_log_level == "info"

    def test_custom_values(self):
        """Test that NetworkConfig accepts custom values."""
        config = NetworkConfig(
            default_port=5000,
            host="127.0.0.1",
            user_agent="CustomBot/1.0",
            uvicorn_log_level="debug",
        )
        assert config.default_port == 5000
        assert config.host == "127.0.0.1"
        assert config.user_agent == "CustomBot/1.0"
        assert config.uvicorn_log_level == "debug"


class TestEndpointConfig:
    """Tests for EndpointConfig."""

    def test_default_values(self):
        """Test that EndpointConfig has correct default values."""
        config = EndpointConfig()
        assert config.bot_api_base_url == "https://smba.trafficmanager.net/teams"
        assert config.activity_path == "/api/messages"
        assert config.health_check_path == "/"

    def test_custom_values(self):
        """Test that EndpointConfig accepts custom values."""
        config = EndpointConfig(
            bot_api_base_url="https://custom.api.com",
            activity_path="/custom/messages",
            health_check_path="/health",
        )
        assert config.bot_api_base_url == "https://custom.api.com"
        assert config.activity_path == "/custom/messages"
        assert config.health_check_path == "/health"


class TestAuthConfig:
    """Tests for AuthConfig."""

    def test_default_values(self):
        """Test that AuthConfig has correct default values."""
        config = AuthConfig()
        assert config.jwt_leeway_seconds == 300
        assert config.bot_framework_issuer == "https://api.botframework.com"
        assert config.bot_framework_jwks_uri == "https://login.botframework.com/v1/.well-known/keys"
        assert config.entra_id_issuer_template == "https://login.microsoftonline.com/{tenant_id}/v2.0"
        assert (
            config.entra_id_jwks_uri_template
            == "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        )
        assert config.default_graph_tenant_id == "botframework.com"

    def test_custom_values(self):
        """Test that AuthConfig accepts custom values."""
        config = AuthConfig(
            jwt_leeway_seconds=600,
            bot_framework_issuer="https://custom.issuer.com",
            default_graph_tenant_id="custom.tenant.com",
        )
        assert config.jwt_leeway_seconds == 600
        assert config.bot_framework_issuer == "https://custom.issuer.com"
        assert config.default_graph_tenant_id == "custom.tenant.com"


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_values(self):
        """Test that RetryConfig has correct default values."""
        config = RetryConfig()
        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0
        assert config.jitter_type == "full"

    def test_custom_values(self):
        """Test that RetryConfig accepts custom values."""
        config = RetryConfig(max_attempts=10, initial_delay=1.0, max_delay=60.0, jitter_type="equal")
        assert config.max_attempts == 10
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter_type == "equal"


class TestSignInConfig:
    """Tests for SignInConfig."""

    def test_default_values(self):
        """Test that SignInConfig has correct default values."""
        config = SignInConfig()
        assert config.oauth_card_text == "Please Sign In..."
        assert config.sign_in_button_text == "Sign In"

    def test_custom_values(self):
        """Test that SignInConfig accepts custom values."""
        config = SignInConfig(oauth_card_text="Custom Sign In Text", sign_in_button_text="Custom Button")
        assert config.oauth_card_text == "Custom Sign In Text"
        assert config.sign_in_button_text == "Custom Button"


class TestLoggerConfig:
    """Tests for LoggerConfig."""

    def test_default_values(self):
        """Test that LoggerConfig has correct default values."""
        config = LoggerConfig()
        assert config.app_logger_name == "@teams/app"
        assert config.http_plugin_logger_name == "@teams/http-plugin"
        assert config.token_validator_logger_name == "@teams/token-validator"
        assert config.http_stream_logger_name == "@teams/http-stream"
        assert config.retry_logger_name == "@teams/retry"

    def test_custom_values(self):
        """Test that LoggerConfig accepts custom values."""
        config = LoggerConfig(
            app_logger_name="custom-app", http_plugin_logger_name="custom-http", retry_logger_name="custom-retry"
        )
        assert config.app_logger_name == "custom-app"
        assert config.http_plugin_logger_name == "custom-http"
        assert config.retry_logger_name == "custom-retry"


class TestPluginConfig:
    """Tests for PluginConfig."""

    def test_default_values(self):
        """Test that PluginConfig has correct default values."""
        config = PluginConfig()
        assert config.metadata_key == "teams:plugin"

    def test_custom_values(self):
        """Test that PluginConfig accepts custom values."""
        config = PluginConfig(metadata_key="custom:plugin")
        assert config.metadata_key == "custom:plugin"


class TestAppConfig:
    """Tests for AppConfig."""

    def test_default_values(self):
        """Test that AppConfig creates all sub-configs with defaults."""
        config = AppConfig()

        # Check that all sub-configs are created
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.endpoints, EndpointConfig)
        assert isinstance(config.auth, AuthConfig)
        assert isinstance(config.retry, RetryConfig)
        assert isinstance(config.signin, SignInConfig)
        assert isinstance(config.logger, LoggerConfig)
        assert isinstance(config.plugin, PluginConfig)

        # Spot check some defaults
        assert config.network.default_port == 3978
        assert config.endpoints.activity_path == "/api/messages"
        assert config.auth.jwt_leeway_seconds == 300
        assert config.retry.max_attempts == 5
        assert config.signin.oauth_card_text == "Please Sign In..."

    def test_custom_network_config(self):
        """Test that AppConfig accepts custom NetworkConfig."""
        network = NetworkConfig(default_port=5000, user_agent="CustomBot/1.0")
        config = AppConfig(network=network)

        assert config.network.default_port == 5000
        assert config.network.user_agent == "CustomBot/1.0"
        # Other sub-configs should still have defaults
        assert config.endpoints.activity_path == "/api/messages"

    def test_multiple_custom_configs(self):
        """Test that AppConfig accepts multiple custom sub-configs."""
        network = NetworkConfig(default_port=8080)
        auth = AuthConfig(jwt_leeway_seconds=600)
        retry = RetryConfig(max_attempts=10)

        config = AppConfig(network=network, auth=auth, retry=retry)

        assert config.network.default_port == 8080
        assert config.auth.jwt_leeway_seconds == 600
        assert config.retry.max_attempts == 10
        # Other configs should still have defaults
        assert config.signin.oauth_card_text == "Please Sign In..."

    def test_fully_custom_config(self):
        """Test creating a fully customized AppConfig."""
        config = AppConfig(
            network=NetworkConfig(default_port=9000, host="localhost"),
            endpoints=EndpointConfig(activity_path="/custom/api"),
            auth=AuthConfig(jwt_leeway_seconds=120),
            retry=RetryConfig(max_attempts=3, jitter_type="none"),
            signin=SignInConfig(oauth_card_text="Login Required"),
            logger=LoggerConfig(app_logger_name="my-app"),
            plugin=PluginConfig(metadata_key="my:plugin"),
        )

        assert config.network.default_port == 9000
        assert config.network.host == "localhost"
        assert config.endpoints.activity_path == "/custom/api"
        assert config.auth.jwt_leeway_seconds == 120
        assert config.retry.max_attempts == 3
        assert config.retry.jitter_type == "none"
        assert config.signin.oauth_card_text == "Login Required"
        assert config.logger.app_logger_name == "my-app"
        assert config.plugin.metadata_key == "my:plugin"

    def test_config_immutability(self):
        """Test that config values can be modified after creation."""
        config = AppConfig()

        # Dataclasses are mutable by default, which is fine for configuration
        config.network.default_port = 7000
        assert config.network.default_port == 7000

    def test_config_types(self):
        """Test that config accepts correct types."""
        # This should not raise any type errors
        config = AppConfig(
            network=NetworkConfig(default_port=5000),
            retry=RetryConfig(max_attempts=10, initial_delay=1.0, max_delay=60.0, jitter_type="equal"),
        )

        assert isinstance(config.network.default_port, int)
        assert isinstance(config.retry.initial_delay, float)
        assert config.retry.jitter_type in ["none", "full", "equal", "decorrelated"]
