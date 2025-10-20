"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for the AppConfig and related configuration classes.
"""


from microsoft.teams.apps.config import (
    AppConfig,
    AuthConfig,
    CredentialsConfig,
    EndpointConfig,
    NetworkConfig,
    SignInConfig,
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
        assert config.api_base_url == "https://smba.trafficmanager.net/teams"
        assert config.activity_path == "/api/messages"

    def test_custom_values(self):
        """Test that EndpointConfig accepts custom values."""
        config = EndpointConfig(
            api_base_url="https://custom.api.com",
            activity_path="/custom/messages",
        )
        assert config.api_base_url == "https://custom.api.com"
        assert config.activity_path == "/custom/messages"

    def test_env_vars(self, monkeypatch):
        """Test that EndpointConfig uses environment variables."""
        monkeypatch.setenv("API_BASE_URL", "https://env.api.com")
        monkeypatch.setenv("ACTIVITY_PATH", "/env/messages")
        config = EndpointConfig()
        assert config.api_base_url == "https://env.api.com"
        assert config.activity_path == "/env/messages"

    def test_explicit_overrides_env_vars(self, monkeypatch):
        """Test that explicit values override env vars."""
        monkeypatch.setenv("API_BASE_URL", "https://env.api.com")
        config = EndpointConfig(api_base_url="https://explicit.api.com")
        assert config.api_base_url == "https://explicit.api.com"


class TestAuthConfig:
    """Tests for AuthConfig."""

    def test_default_values(self):
        """Test that AuthConfig has correct default values (None when env vars not set)."""
        config = AuthConfig()
        assert config.jwt_leeway_seconds is None
        assert config.bot_framework_issuer is None
        assert config.bot_framework_jwks_uri is None
        assert config.entra_id_issuer_template is None
        assert config.entra_id_jwks_uri_template is None

    def test_custom_values(self):
        """Test that AuthConfig accepts custom values."""
        config = AuthConfig(
            jwt_leeway_seconds=600,
            bot_framework_issuer="https://custom.botframework.com",
            bot_framework_jwks_uri="https://custom.keys.com",
            entra_id_issuer_template="https://custom.entra.com/{tenant_id}/v2.0",
            entra_id_jwks_uri_template="https://custom.entra.com/{tenant_id}/keys",
        )
        assert config.jwt_leeway_seconds == 600
        assert config.bot_framework_issuer == "https://custom.botframework.com"
        assert config.bot_framework_jwks_uri == "https://custom.keys.com"
        assert config.entra_id_issuer_template == "https://custom.entra.com/{tenant_id}/v2.0"
        assert config.entra_id_jwks_uri_template == "https://custom.entra.com/{tenant_id}/keys"

    def test_env_vars(self, monkeypatch):
        """Test that AuthConfig uses environment variables."""
        monkeypatch.setenv("JWT_LEEWAY_SECONDS", "900")
        monkeypatch.setenv("BOT_FRAMEWORK_ISSUER", "https://env.botframework.com")
        monkeypatch.setenv("BOT_FRAMEWORK_JWKS_URI", "https://env.keys.com")
        monkeypatch.setenv("ENTRA_ID_ISSUER_TEMPLATE", "https://env.entra.com/{tenant_id}/v2.0")
        monkeypatch.setenv("ENTRA_ID_JWKS_URI_TEMPLATE", "https://env.entra.com/{tenant_id}/keys")
        config = AuthConfig()
        assert config.jwt_leeway_seconds == 900
        assert config.bot_framework_issuer == "https://env.botframework.com"
        assert config.bot_framework_jwks_uri == "https://env.keys.com"
        assert config.entra_id_issuer_template == "https://env.entra.com/{tenant_id}/v2.0"
        assert config.entra_id_jwks_uri_template == "https://env.entra.com/{tenant_id}/keys"

    def test_explicit_overrides_env_vars(self, monkeypatch):
        """Test that explicit values override environment variables."""
        monkeypatch.setenv("JWT_LEEWAY_SECONDS", "900")
        config = AuthConfig(jwt_leeway_seconds=1200)
        assert config.jwt_leeway_seconds == 1200


class TestSignInConfig:
    """Tests for SignInConfig."""

    def test_default_values(self):
        """Test that SignInConfig has correct default values."""
        config = SignInConfig()
        assert config.oauth_card_text == "Please Sign In..."
        assert config.sign_in_button_text == "Sign In"

    def test_custom_values(self):
        """Test that SignInConfig accepts custom values."""
        config = SignInConfig(
            oauth_card_text="Custom Sign In Text",
            sign_in_button_text="Custom Button",
        )
        assert config.oauth_card_text == "Custom Sign In Text"
        assert config.sign_in_button_text == "Custom Button"

    def test_env_vars(self, monkeypatch):
        """Test that SignInConfig uses environment variables."""
        monkeypatch.setenv("OAUTH_CARD_TEXT", "Env Card Text")
        monkeypatch.setenv("SIGN_IN_BUTTON_TEXT", "Env Button")
        config = SignInConfig()
        assert config.oauth_card_text == "Env Card Text"
        assert config.sign_in_button_text == "Env Button"

    def test_explicit_overrides_env_vars(self, monkeypatch):
        """Test that explicit values override env vars."""
        monkeypatch.setenv("OAUTH_CARD_TEXT", "Env Card Text")
        config = SignInConfig(oauth_card_text="Explicit Card Text")
        assert config.oauth_card_text == "Explicit Card Text"


class TestCredentialsConfig:
    """Tests for CredentialsConfig."""

    def test_default_values(self):
        """Test that CredentialsConfig has correct default values (None if no env vars)."""
        config = CredentialsConfig()
        # Values will be None if env vars are not set
        assert config.client_id is None or isinstance(config.client_id, str)
        assert config.client_secret is None or isinstance(config.client_secret, str)
        assert config.tenant_id is None or isinstance(config.tenant_id, str)

    def test_custom_values(self):
        """Test that CredentialsConfig accepts custom values."""
        config = CredentialsConfig(
            client_id="custom-client-id",
            client_secret="custom-client-secret",
            tenant_id="custom-tenant-id",
        )
        assert config.client_id == "custom-client-id"
        assert config.client_secret == "custom-client-secret"
        assert config.tenant_id == "custom-tenant-id"

    def test_env_vars(self, monkeypatch):
        """Test that CredentialsConfig uses environment variables."""
        monkeypatch.setenv("CLIENT_ID", "env-client-id")
        monkeypatch.setenv("CLIENT_SECRET", "env-client-secret")
        monkeypatch.setenv("TENANT_ID", "env-tenant-id")
        config = CredentialsConfig()
        assert config.client_id == "env-client-id"
        assert config.client_secret == "env-client-secret"
        assert config.tenant_id == "env-tenant-id"

    def test_explicit_overrides_env_vars(self, monkeypatch):
        """Test that explicit values override env vars."""
        monkeypatch.setenv("CLIENT_ID", "env-client-id")
        config = CredentialsConfig(client_id="explicit-client-id")
        assert config.client_id == "explicit-client-id"


class TestAppConfig:
    """Tests for AppConfig."""

    def test_default_values(self):
        """Test that AppConfig creates all sub-configs with defaults."""
        config = AppConfig()

        # Check that all sub-configs are created
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.endpoints, EndpointConfig)
        assert isinstance(config.auth, AuthConfig)
        assert isinstance(config.signin, SignInConfig)
        # credentials is optional and None by default
        assert config.credentials is None

        # Spot check some defaults
        assert config.network.default_port == 3978
        assert config.endpoints.activity_path == "/api/messages"
        assert config.signin.oauth_card_text == "Please Sign In..."

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
        signin = SignInConfig(oauth_card_text="Custom Sign In")

        config = AppConfig(network=network, signin=signin)

        assert config.network.default_port == 8080
        assert config.signin.oauth_card_text == "Custom Sign In"

    def test_fully_custom_config(self):
        """Test creating a fully customized AppConfig."""
        config = AppConfig(
            network=NetworkConfig(default_port=9000),
            endpoints=EndpointConfig(activity_path="/custom/api"),
            signin=SignInConfig(oauth_card_text="Custom Sign In"),
        )

        assert config.network.default_port == 9000
        assert config.endpoints.activity_path == "/custom/api"
        assert config.signin.oauth_card_text == "Custom Sign In"

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

        config = AppConfig()

        assert config.network.default_port == 7070
        assert config.endpoints.activity_path == "/env/api"

    def test_credentials_config(self, monkeypatch):
        """Test that credentials can be set via AppConfig."""
        monkeypatch.setenv("CLIENT_ID", "test-client-id")
        monkeypatch.setenv("CLIENT_SECRET", "test-client-secret")

        # Without credentials in config
        config1 = AppConfig()
        assert config1.credentials is None

        # With credentials in config
        config2 = AppConfig(
            credentials=CredentialsConfig(
                client_id="explicit-client-id",
                client_secret="explicit-client-secret",
                tenant_id="explicit-tenant-id",
            )
        )
        assert config2.credentials.client_id == "explicit-client-id"
        assert config2.credentials.client_secret == "explicit-client-secret"
        assert config2.credentials.tenant_id == "explicit-tenant-id"
