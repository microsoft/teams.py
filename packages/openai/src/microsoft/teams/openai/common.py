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
    model: str | None = None
    key: str | None = None
    client: AsyncOpenAI | None = None
    mode: Literal["completions", "responses"] = "responses"
    base_url: str | None = None
    # Azure OpenAI options
    azure_endpoint: str | None = None
    api_version: str | None = None
    logger: Logger = field(default_factory=lambda: ConsoleLogger().create_logger(name="OpenAI-Model"))
    _client: AsyncOpenAI = field(init=False)
    _model: str = field(init=False)

    def __post_init__(self):
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
