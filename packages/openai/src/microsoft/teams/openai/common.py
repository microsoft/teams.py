"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Literal

from microsoft.teams.common.logging import ConsoleLogger

from openai import AsyncAzureOpenAI, AsyncOpenAI


@dataclass
class OpenAIBaseModel:
    """
    Base configuration class for OpenAI model implementations.

    Provides common configuration for both Azure OpenAI and standard OpenAI,
    including client initialization and authentication setup.
    """

    model: str  # Model name (e.g., "gpt-4", "gpt-3.5-turbo")
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

    def __post_init__(self):
        """
        Initialize the OpenAI client after dataclass initialization.

        Creates either an Azure OpenAI client or standard OpenAI client
        based on the provided configuration parameters.

        Raises:
            ValueError: If neither key nor client is provided
        """
        if self.client is None and self.key is None:
            raise ValueError("Either key or client is required when initializing an OpenAIModel")
        elif self.client is not None:
            self._client = self.client
        else:
            # key is the API key
            if self.azure_endpoint:
                self._client = AsyncAzureOpenAI(
                    api_key=self.key, azure_endpoint=self.azure_endpoint, api_version=self.api_version
                )
            else:
                self._client = AsyncOpenAI(api_key=self.key, base_url=self.base_url)
