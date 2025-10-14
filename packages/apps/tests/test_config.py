"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for the AppConfig and related configuration classes.
"""


from microsoft.teams.apps.config import (
    AppConfig,
    AuthConfig,
    EndpointConfig,
    NetworkConfig,
)


class TestNetworkConfig:
    """Tests for NetworkConfig."""

    def test_default_values(self):
        """Test that NetworkConfig has correct default values."""
        config = NetworkConfig()
        assert config.default_port == 3978

    def test_custom_values(self):
        """Test that NetworkConfig accepts custom values."""
        config = NetworkConfig(
            default_port=5000,
        )
        assert config.default_port == 5000

    def test_env_var_port(self, monkeypatch):
        """Test that NetworkConfig uses PORT env var."""
        monkeypatch.setenv("PORT", "8080")
        config = NetworkConfig()
        assert config.default_port == 8080

    def test_explicit_overrides_env_var(self, monkeypatch):
        """Test that explicit values override env vars."""
        monkeypatch.setenv("PORT", "8080")
        config = NetworkConfig(default_port=9000)
        assert config.default_port == 9000


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

    def test_env_vars(self, monkeypatch):
        """Test that EndpointConfig uses environment variables."""
        monkeypatch.setenv("BOT_API_BASE_URL", "https://env.api.com")
        monkeypatch.setenv("ACTIVITY_PATH", "/env/messages")
        monkeypatch.setenv("HEALTH_CHECK_PATH", "/env/health")
        config = EndpointConfig()
        assert config.bot_api_base_url == "https://env.api.com"
        assert config.activity_path == "/env/messages"
        assert config.health_check_path == "/env/health"

    def test_explicit_overrides_env_vars(self, monkeypatch):
        """Test that explicit values override env vars."""
        monkeypatch.setenv("BOT_API_BASE_URL", "https://env.api.com")
        config = EndpointConfig(bot_api_base_url="https://explicit.api.com")
        assert config.bot_api_base_url == "https://explicit.api.com"


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

    def test_env_vars(self, monkeypatch):
        """Test that AuthConfig uses environment variables."""
        monkeypatch.setenv("JWT_LEEWAY_SECONDS", "600")
        monkeypatch.setenv("BOT_FRAMEWORK_ISSUER", "https://env.issuer.com")
        monkeypatch.setenv("DEFAULT_GRAPH_TENANT_ID", "env.tenant.com")
        config = AuthConfig()
        assert config.jwt_leeway_seconds == 600
        assert config.bot_framework_issuer == "https://env.issuer.com"
        assert config.default_graph_tenant_id == "env.tenant.com"

    def test_explicit_overrides_env_vars(self, monkeypatch):
        """Test that explicit values override env vars."""
        monkeypatch.setenv("JWT_LEEWAY_SECONDS", "600")
        config = AuthConfig(jwt_leeway_seconds=900)
        assert config.jwt_leeway_seconds == 900


class TestAppConfig:
    """Tests for AppConfig."""

    def test_default_values(self):
        """Test that AppConfig creates all sub-configs with defaults."""
        config = AppConfig()

        # Check that all sub-configs are created
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.endpoints, EndpointConfig)
        assert isinstance(config.auth, AuthConfig)

        # Spot check some defaults
        assert config.network.default_port == 3978
        assert config.endpoints.activity_path == "/api/messages"
        assert config.auth.jwt_leeway_seconds == 300

    def test_custom_network_config(self):
        """Test that AppConfig accepts custom NetworkConfig."""
        network = NetworkConfig(default_port=5000)
        config = AppConfig(network=network)

        assert config.network.default_port == 5000
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
        )

        assert config.network.default_port == 9000
        assert config.endpoints.activity_path == "/custom/api"
        assert config.auth.jwt_leeway_seconds == 120

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

    def test_env_vars_propagate(self, monkeypatch):
        """Test that env vars propagate through AppConfig."""
        monkeypatch.setenv("PORT", "7070")
        monkeypatch.setenv("ACTIVITY_PATH", "/env/api")
        monkeypatch.setenv("JWT_LEEWAY_SECONDS", "450")

        config = AppConfig()

        assert config.network.default_port == 7070
        assert config.endpoints.activity_path == "/env/api"
        assert config.auth.jwt_leeway_seconds == 450
