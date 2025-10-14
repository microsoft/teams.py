"""
Example showing how to use AppConfig in a Teams bot application.

This is a demonstration of the new AppConfig feature that makes all
hardcoded constants in microsoft-teams-apps user-configurable.
"""

import asyncio
import os

from microsoft.teams.apps import App, AppConfig, NetworkConfig, AuthConfig, RetryConfig, SignInConfig


def get_development_config() -> AppConfig:
    """
    Create a development-friendly configuration.
    
    This config is optimized for local development with:
    - Localhost binding
    - Debug logging
    - Forgiving JWT validation
    - Verbose retry logging
    """
    return AppConfig(
        network=NetworkConfig(
            default_port=3978,
            host="127.0.0.1",  # Only bind to localhost for security
            user_agent="MyTeamsBot/1.0-dev",
            uvicorn_log_level="debug"  # Verbose server logs
        ),
        auth=AuthConfig(
            jwt_leeway_seconds=600  # 10 minutes - forgiving for clock skew
        ),
        retry=RetryConfig(
            max_attempts=3,  # Fail faster in development
            initial_delay=0.5,
            max_delay=10.0
        ),
        signin=SignInConfig(
            oauth_card_text="Development Mode - Please Sign In",
            sign_in_button_text="Sign In (Dev)"
        )
    )


def get_production_config() -> AppConfig:
    """
    Create a production-ready configuration.
    
    This config is optimized for production with:
    - Public binding
    - Warning-level logging
    - Standard JWT validation
    - Aggressive retry strategy
    """
    return AppConfig(
        network=NetworkConfig(
            default_port=8080,
            host="0.0.0.0",  # Bind to all interfaces
            user_agent="MyTeamsBot/1.0",
            uvicorn_log_level="warning"  # Less verbose in production
        ),
        auth=AuthConfig(
            jwt_leeway_seconds=300  # 5 minutes - standard
        ),
        retry=RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=30.0,
            jitter_type="equal"  # Prevent thundering herd
        ),
        signin=SignInConfig(
            oauth_card_text="Please sign in to continue",
            sign_in_button_text="Sign In"
        )
    )


def main():
    """Main entry point for the bot application."""
    
    # Determine environment
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Select appropriate configuration
    if environment == "production":
        config = get_production_config()
        print("🚀 Starting in PRODUCTION mode")
    else:
        config = get_development_config()
        print("🔧 Starting in DEVELOPMENT mode")
    
    # Print configuration info
    print(f"  - Port: {config.network.default_port}")
    print(f"  - Host: {config.network.host}")
    print(f"  - User-Agent: {config.network.user_agent}")
    print(f"  - Max Retries: {config.retry.max_attempts}")
    print(f"  - JWT Leeway: {config.auth.jwt_leeway_seconds}s")
    
    # Create the app with the selected configuration
    app = App(
        client_id=os.getenv("CLIENT_ID", "your-client-id"),
        client_secret=os.getenv("CLIENT_SECRET", "your-client-secret"),
        tenant_id=os.getenv("TENANT_ID", "your-tenant-id"),
        # Pass the config to the app
        # config=config  # TODO: Uncomment when App supports config parameter
    )
    
    # Register a simple message handler
    @app.on_message
    async def on_message(ctx):
        """Handle incoming messages."""
        await ctx.send(f"Echo: {ctx.activity.text}")
    
    # Start the app
    print(f"\n✅ App configured! Ready to start on port {config.network.default_port}")
    print("   (Config object created but not yet integrated with App class)")
    
    # In a real app, you would call:
    # asyncio.run(app.start())


if __name__ == "__main__":
    main()
    print("\n📝 Note: Full integration with App class is pending.")
    print("   This example demonstrates the Config API design.")
