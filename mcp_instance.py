import subprocess
import os
import sys
import time
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams


class MCPInstance():
    process = None
    def __init__(self, project_path: str):
        self.project_path = project_path
        if MCPInstance.process is not None:
            raise RuntimeError("MCPInstance already running")
        MCPInstance.process = None

    def start(self):
        os.makedirs(self.project_path, exist_ok=True)
        
        print("\n🔌 Starting MCP server in HTTP mode...")
        mcp_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
        self.mcp_host = "127.0.0.1"
        self.mcp_port = 8000
        
        # Start MCP server as a subprocess in HTTP mode
        MCPInstance.process = subprocess.Popen(
            [sys.executable, mcp_script, self.project_path, "--transport", "http", "--host", self.mcp_host, "--port", str(self.mcp_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    def get_toolset(self, allowed_tools=None):
        mcp_params = {}
        if allowed_tools:
            mcp_params['tool_filter'] = allowed_tools

        return McpToolset(connection_params=StreamableHTTPConnectionParams(
                url=f"http://{self.mcp_host}:{self.mcp_port}/mcp",
                timeout=60.0,
                sse_read_timeout=300.0,
                terminate_on_close=False  # We'll manage termination in finally block
            ), 
            **mcp_params)

    def stop(self):
        # Terminate MCP server
        if MCPInstance.process:
            print("🛑 Stopping MCP server...")
            MCPInstance.process.terminate()
            try:
                MCPInstance.process.wait(timeout=5)
                print("✅ MCP server stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  MCP server did not stop gracefully, killing...")
                MCPInstance.process.kill()
                MCPInstance.process.wait()
