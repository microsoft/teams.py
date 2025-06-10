"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""


from __future__ import annotations

import json
import logging

from .ansi import ANSI


class ConsoleFormatter(logging.Formatter):    
    _colors = {
        'ERROR': ANSI.FOREGROUND_RED,
        'WARNING': ANSI.FOREGROUND_YELLOW,
        'INFO': ANSI.FOREGROUND_CYAN,
        'DEBUG': ANSI.FOREGROUND_MAGENTA,
    }

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, (dict, list)):
            record.msg = json.dumps(record.msg, indent=2)
        
        level_name = record.levelname.upper()
        color = self._colors.get(level_name, '')
        prefix = f"{color}{ANSI.BOLD}[{level_name}]"
        name = f"{record.name}{ANSI.FOREGROUND_RESET}{ANSI.BOLD_RESET}"
        
        message = str(record.msg)
        lines = message.split('\n')
        formatted_lines = [f"{prefix} {name} {line}" for line in lines]
        return '\n'.join(formatted_lines)