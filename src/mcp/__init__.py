"""
DPOS MCP (Model Context Protocol) Server
Exposes DPOS tools for use with Claude and other MCP clients.
"""

from src.mcp.server import create_mcp_server
from src.mcp.tools import get_all_tools

__all__ = ["create_mcp_server", "get_all_tools"]
