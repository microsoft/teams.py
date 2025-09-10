"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from os import getenv
from typing import Literal

from dotenv import find_dotenv, load_dotenv
from microsoft.teams.common.logging import ConsoleLogger

from openai import AsyncAzureOpenAI, AsyncOpenAI

load_dotenv(find_dotenv(usecwd=True))


@dataclass
class OpenAIBaseModel:
    """
    Base configuration class for OpenAI model implementations.

    Provides common configuration for both Azure OpenAI and standard OpenAI,
    including client initialization and authentication setup. Supports both
    explicit configuration and environment variable fallbacks.

    Environment Variables:
        AZURE_OPENAI_MODEL or OPENAI_MODEL: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
        AZURE_OPENAI_API_KEY or OPENAI_API_KEY: API key for authentication
        AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
        AZURE_OPENAI_API_VERSION: Azure OpenAI API version
        OPENAI_BASE_URL: Custom base URL for OpenAI API

    Note:
        Environment variables are only used when the corresponding parameter is not provided.
        Azure configuration takes precedence when AZURE_OPENAI_ENDPOINT is available.
    """

    model: str | None = None  # Model name (e.g., "gpt-4", "gpt-3.5-turbo")
    key: str | None = None  # API key for authentication
    client: AsyncOpenAI | None = None  # Pre-configured client instance
    mode: Literal["completions", "responses"] = "responses"  # API mode to use
    base_url: str | None = None  # Custom base URL for OpenAI API
    # Azure OpenAI options
    azure_endpoint: str | None = None  # Azure OpenAI endpoint URL
    api_version: str | None = None  # Azure OpenAI API version
    logger: Logger = field(
        default_factory=lambda: ConsoleLogger().create_logger(name="OpenAI-Model")
    )  # Logger instance
    _client: AsyncOpenAI = field(init=False)  # Internal client instance
    _model: str = field(init=False)  # Resolved model name

    def __post_init__(self):
        """
        Initialize the OpenAI client after dataclass initialization.

        Creates either an Azure OpenAI client or standard OpenAI client
        based on the provided configuration parameters. Falls back to
        environment variables when parameters are not provided.

        Raises:
            ValueError: If required configuration is missing
        """
        # Get model from env if not provided
        if self.model is None:
            env_model = getenv("AZURE_OPENAI_MODEL") or getenv("OPENAI_MODEL")
            if not env_model:
                raise ValueError(
                    "Model is required. Set AZURE_OPENAI_MODEL/OPENAI_MODEL env var or provide model parameter."
                )
            else:
                self._model = env_model
        else:
            self._model = self.model

        # Get API key from env if not provided (and no client provided)
        if self.client is None and self.key is None:
            self.key = getenv("AZURE_OPENAI_API_KEY") or getenv("OPENAI_API_KEY")
            if not self.key:
                raise ValueError(
                    "API key is required. Set AZURE_OPENAI_API_KEY/OPENAI_API_KEY env var or provide key parameter."
                )

        # Get Azure endpoint from env if not provided
        if self.azure_endpoint is None:
            self.azure_endpoint = getenv("AZURE_OPENAI_ENDPOINT")

        # Get API version from env if not provided
        if self.api_version is None:
            self.api_version = getenv("AZURE_OPENAI_API_VERSION")

        # Get base URL from env if not provided
        if self.base_url is None:
            self.base_url = getenv("OPENAI_BASE_URL")

        # Initialize the client
        if self.client is not None:
            self._client = self.client
        else:
            # Create client based on configuration
            if self.azure_endpoint:
                self._client = AsyncAzureOpenAI(
                    api_key=self.key, azure_endpoint=self.azure_endpoint, api_version=self.api_version
                )
            else:
                self._client = AsyncOpenAI(api_key=self.key, base_url=self.base_url)
