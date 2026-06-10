"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

from .adapter import BotBuilderAdapter, BotBuilderAdapterOptions

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["BotBuilderAdapter", "BotBuilderAdapterOptions"]
