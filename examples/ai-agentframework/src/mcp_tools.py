"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from agent_framework import MCPStreamableHTTPTool

mcp_tools = [
    MCPStreamableHTTPTool(name="MSLearn", url="https://learn.microsoft.com/api/mcp"),
]
