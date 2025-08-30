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
    model: str
    key: str | None = None
    client: AsyncOpenAI | None = None
    mode: Literal["completions", "responses"] = "responses"
    base_url: str | None = None
    # Azure OpenAI options
    azure_endpoint: str | None = None
    api_version: str | None = None
    logger: Logger = field(default_factory=lambda: ConsoleLogger().create_logger(name="OpenAI-Model"))
    _client: AsyncOpenAI = field(init=False)

    def __post_init__(self):
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
