"""
MCP Server for DPOS
Model Context Protocol server implementation using FastMCP.
Exposes DPOS tools for Claude Desktop and other MCP clients.
"""
import json
import sys
import inspect
from typing import Any, Dict, List, Optional, get_type_hints

# Try to import mcp library
try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    FastMCP = None

from dpos_mcp.tools import get_all_tools, get_tool_descriptions


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
        self._build_tool_schemas()

    def _build_tool_schemas(self):
        """Build proper JSON schemas for all tools."""
        self.tool_schemas = {}
        
        for name, tool in self.tools.items():
            schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            # Try to extract from Pydantic schema if available
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    pydantic_schema = tool.args_schema.schema()
                    schema["properties"] = pydantic_schema.get("properties", {})
                    schema["required"] = pydantic_schema.get("required", [])
                    
                    # Add descriptions from field info
                    for prop_name, prop_info in schema["properties"].items():
                        if "description" not in prop_info:
                            prop_info["description"] = f"The {prop_name} parameter"
                except:
                    pass
            else:
                # Fallback to function signature
                try:
                    func = tool.func if hasattr(tool, 'func') else tool
                    sig = inspect.signature(func)
                    
                    for param_name, param in sig.parameters.items():
                        if param_name in ['self', 'cls']:
                            continue
                        
                        # Get type annotation
                        param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
                        param_type_str = self._python_type_to_json_type(param_type)
                        
                        schema["properties"][param_name] = {
                            "type": param_type_str,
                            "description": f"Parameter {param_name}"
                        }
                        
                        if param.default == inspect.Parameter.empty:
                            schema["required"].append(param_name)
                            
                except Exception as e:
                    # Simple schema
                    schema = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
            
            self.tool_schemas[name] = schema
            
    def _python_type_to_json_type(self, python_type) -> str:
        """Convert Python type to JSON schema type."""
        type_str = str(python_type)
        
        if python_type == str:
            return "string"
        elif python_type == int:
            return "integer"
        elif python_type == float:
            return "number"
        elif python_type == bool:
            return "boolean"
        elif python_type == list or 'List' in type_str or 'list' in type_str:
            return "array"
        elif python_type == dict or 'Dict' in type_str or 'dict' in type_str:
            return "object"
        elif 'Optional' in type_str:
            # Extract inner type from Optional[Type]
            inner_type = type_str.replace('Optional[', '').replace(']', '')
            return self._python_type_to_json_type(eval(inner_type) if '[' not in inner_type else 'string')
        else:
            return "string"

    def handle_request(self, request: Dict) -> Optional[Dict]:
        """Handle an incoming MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Handle notifications (requests without ID)
        if request_id is None:
            return None

        if method == "initialize":
            return self._handle_initialize(request_id, params)
        elif method == "tools/list":
            return self._handle_list_tools(request_id)
        elif method == "tools/call":
            return self._handle_call_tool(request_id, params)
        elif method == "shutdown":
            return self._handle_shutdown(request_id)
        else:
            return self._error_response(request_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, request_id: Any, params: Dict) -> Dict:
        """Handle initialization request."""
        client_version = params.get("protocolVersion", "2025-06-18")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": client_version,
                "serverInfo": {
                    "name": "dpos-mcp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {
                        "list": True,
                        "call": True
                    },
                    "notifications": {}
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
                "inputSchema": self.tool_schemas.get(name, {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
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
            return self._error_response(request_id, -32601, f"Unknown tool: {tool_name}")

        try:
            tool = self.tools[tool_name]
            
            # Validate arguments against schema
            schema = self.tool_schemas.get(tool_name, {})
            required_params = schema.get("required", [])
            
            for param in required_params:
                if param not in arguments:
                    return self._error_response(
                        request_id, 
                        -32602, 
                        f"Missing required parameter: {param}"
                    )
            
            # Call the tool
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
        except TypeError as e:
            return self._error_response(request_id, -32602, f"Invalid parameters: {str(e)}")
        except Exception as e:
            return self._error_response(request_id, -32000, f"Tool execution failed: {str(e)}")

    def _handle_shutdown(self, request_id: Any) -> Dict:
        """Handle shutdown request."""
        print("MCP Server shutting down...", file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": None
        }

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    def run(self):
        """Run the server, reading from stdin and writing to stdout."""
        print("DPOS MCP Server started. Listening for requests...", file=sys.stderr)

        while True:
            line = sys.stdin.readline()
            if not line:
                # EOF reached, exit gracefully
                print("EOF reached, shutting down...", file=sys.stderr)
                break

            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response:  # Only send response for requests with ID
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
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32000,
                        "message": f"Internal error: {e}"
                    }
                }
                print(json.dumps(error_response), flush=True)


def run_stdio_server():
    """Run the stdio-based MCP server."""
    server = StdioMCPServer()
    server.run()


if __name__ == "__main__":
    run_stdio_server()