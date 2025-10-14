"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for the AppConfig and related configuration classes.
"""


from microsoft.teams.apps.config import (
    AppConfig,
    AuthConfig,
    EndpointConfig,
    LoggerConfig,
    NetworkConfig,
)


class TestNetworkConfig:
    """Tests for NetworkConfig."""

    def test_default_values(self):
        """Test that NetworkConfig has correct default values."""
        config = NetworkConfig()
        assert config.default_port == 3978
        assert config.user_agent is None

    def test_custom_values(self):
        """Test that NetworkConfig accepts custom values."""
        config = NetworkConfig(
            default_port=5000,
            user_agent="CustomBot/1.0",
        )
        assert config.default_port == 5000
        assert config.user_agent == "CustomBot/1.0"


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


class TestAppConfig:
    """Tests for AppConfig."""

    def test_default_values(self):
        """Test that AppConfig creates all sub-configs with defaults."""
        config = AppConfig()

        # Check that all sub-configs are created
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.endpoints, EndpointConfig)
        assert isinstance(config.auth, AuthConfig)
        assert isinstance(config.logger, LoggerConfig)

        # Spot check some defaults
        assert config.network.default_port == 3978
        assert config.endpoints.activity_path == "/api/messages"
        assert config.auth.jwt_leeway_seconds == 300

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

        config = AppConfig(network=network, auth=auth)

        assert config.network.default_port == 8080
        assert config.auth.jwt_leeway_seconds == 600

    def test_fully_custom_config(self):
        """Test creating a fully customized AppConfig."""
        config = AppConfig(
            network=NetworkConfig(default_port=9000),
            endpoints=EndpointConfig(activity_path="/custom/api"),
            auth=AuthConfig(jwt_leeway_seconds=120),
            logger=LoggerConfig(app_logger_name="my-app"),
        )

        assert config.network.default_port == 9000
        assert config.endpoints.activity_path == "/custom/api"
        assert config.auth.jwt_leeway_seconds == 120
        assert config.logger.app_logger_name == "my-app"

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
        )

        assert isinstance(config.network.default_port, int)
