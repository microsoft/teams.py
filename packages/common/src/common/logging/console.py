"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""


from __future__ import annotations

import logging
import os
from typing import Callable, Dict, Optional

from .filter import ConsoleFilter
from .formatter import ConsoleFormatter


class ConsoleLogger:
    _levels = {
        'error': logging.ERROR,
        'warn': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG
    }

    def create_logger(self, name: str, options: Optional[Dict] = None) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.handlers = []
        
        handler = logging.StreamHandler()
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)
        
        level = (os.environ.get('LOG_LEVEL') or 
                (options and options.get('level')) or 
                'info').lower()
        logger.setLevel(self._levels.get(level, logging.INFO))
        
        pattern = (os.environ.get('LOG') or 
                  (options and options.get('pattern')) or 
                  '*')
        logger.addFilter(ConsoleFilter(pattern))
        
        setattr(logger, 'child', self.create_child(logger))
        
        return logger

    def create_child(self, parent_logger: logging.Logger) -> Callable[[str], logging.Logger]:
        def child(name: str) -> logging.Logger:
            return self.create_logger(
                f"{parent_logger.name}/{name}", 
                {'level': logging.getLevelName(parent_logger.level)}
            )
        return child


