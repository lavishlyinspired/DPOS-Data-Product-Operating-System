#!/usr/bin/env python3
"""
DPOS MCP Server Runner
Starts the MCP server for use with Claude Desktop and other MCP clients.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.mcp.server import run_stdio_server


if __name__ == "__main__":
    run_stdio_server()
