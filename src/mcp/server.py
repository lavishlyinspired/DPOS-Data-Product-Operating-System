"""
MCP Server for DPOS
Model Context Protocol server implementation using FastMCP.
Exposes DPOS tools for Claude Desktop and other MCP clients.
"""
import json
import sys
from typing import Any, Dict, List

# Try to import mcp library
try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    FastMCP = None

from src.mcp.tools import get_all_tools, get_tool_descriptions


def create_mcp_server(name: str = "dpos-mcp"):
    """
    Create and configure the MCP server.

    Args:
        name: Server name for identification

    Returns:
        Configured FastMCP server instance
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP library not installed. Install with: pip install mcp"
        )

    # Create FastMCP server
    mcp = FastMCP(name)

    # Register all DPOS tools
    tools = get_all_tools()
    for tool in tools:
        # FastMCP automatically registers decorated functions
        # We need to manually add them here
        mcp.tool()(tool)

    return mcp


class StdioMCPServer:
    """
    Simple MCP server that communicates via stdio.
    Works without the full MCP library.
    """

    def __init__(self):
        self.tools = {t.name: t for t in get_all_tools()}

    def handle_request(self, request: Dict) -> Dict:
        """Handle an incoming MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return self._handle_initialize(request_id)
        elif method == "tools/list":
            return self._handle_list_tools(request_id)
        elif method == "tools/call":
            return self._handle_call_tool(request_id, params)
        else:
            return self._error_response(request_id, f"Unknown method: {method}")

    def _handle_initialize(self, request_id: Any) -> Dict:
        """Handle initialization request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "0.1.0",
                "serverInfo": {
                    "name": "dpos-mcp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }

    def _handle_list_tools(self, request_id: Any) -> Dict:
        """Handle list tools request."""
        tool_list = []
        for name, tool in self.tools.items():
            tool_info = {
                "name": name,
                "description": tool.description or "",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }

            # Extract schema from tool
            if hasattr(tool, 'args_schema') and tool.args_schema:
                schema = tool.args_schema.schema()
                tool_info["inputSchema"]["properties"] = schema.get("properties", {})
                tool_info["inputSchema"]["required"] = schema.get("required", [])

            tool_list.append(tool_info)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tool_list}
        }

    def _handle_call_tool(self, request_id: Any, params: Dict) -> Dict:
        """Handle tool call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return self._error_response(request_id, f"Unknown tool: {tool_name}")

        try:
            tool = self.tools[tool_name]
            result = tool.invoke(arguments)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, default=str)
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error_response(request_id, str(e))

    def _error_response(self, request_id: Any, message: str) -> Dict:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": message
            }
        }

    def run(self):
        """Run the server, reading from stdin and writing to stdout."""
        print("DPOS MCP Server started. Listening for requests...", file=sys.stderr)

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {e}"
                    }
                }
                print(json.dumps(error_response), flush=True)


def run_stdio_server():
    """Run the stdio-based MCP server."""
    server = StdioMCPServer()
    server.run()


if __name__ == "__main__":
    run_stdio_server()
