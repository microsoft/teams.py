"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import warnings

from .completions_model import OpenAICompletionsAIModel
from .responses_chat_model import OpenAIResponsesAIModel

logging.getLogger(__name__).addHandler(logging.NullHandler())

warnings.warn(
    "microsoft-teams-openai is deprecated and will no longer be maintained. "
    "Use the official OpenAI Python SDK instead: https://github.com/openai/openai-python",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["OpenAICompletionsAIModel", "OpenAIResponsesAIModel"]
