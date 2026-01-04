"""
DPOS MCP (Model Context Protocol) Server
Exposes DPOS tools for use with Claude and other MCP clients.
"""

from dpos_mcp.server import create_mcp_server
from dpos_mcp.tools import get_all_tools

__all__ = ["create_mcp_server", "get_all_tools"]
