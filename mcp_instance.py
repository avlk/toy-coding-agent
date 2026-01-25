from multiprocessing.util import debug
import subprocess
import os
import sys
import time
import asyncio
from google.genai.types import FunctionDeclaration
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams


class MCPInstance():
    process = None
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.mcp_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
        self.mcp_host = "127.0.0.1"
        self.mcp_port = 8000
        if MCPInstance.process is not None:
            raise RuntimeError("MCPInstance already running")
        MCPInstance.process = None


    async def start(self) -> bool:
        os.makedirs(self.project_path, exist_ok=True)
        
        print("\n🔌 Starting MCP server in HTTP mode...")
        
        # Start MCP server as a subprocess in HTTP mode
        MCPInstance.process = subprocess.Popen(
            [sys.executable, self.mcp_script, self.project_path, "--transport", "http", "--host", self.mcp_host, "--port", str(self.mcp_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Create internal connection to the server to verify it's up and do utility calls
        timeout = 30  # seconds
        start_time = time.time()
        self._toolset = self.get_toolset()
        while time.time() - start_time < timeout:
            try:
                await asyncio.sleep(5)
                # Try to fetch tools to verify server is up
                tools = await self._toolset.get_tools(readonly_context=None)
                return True
            except asyncio.CancelledError:
                # This is all broken here - if it can't connect, it breaks the whole asyncio loop
                print("MCP server startup was cancelled, not continuing...")
                return False
            except Exception as e:
                print("Waiting for MCP server to start...", str(e))

        return False

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

    async def mcp_toolset_to_function_declarations(cls, mcp_toolset: McpToolset) -> tuple[list, dict]:
        """Convert McpToolset to function declarations for use with streaming API (generate_content_stream).
        
        Returns:
            tuple: (function_declarations list, tool_map dict mapping tool names to MCPTool objects)
        """
        # Try to get existing event loop, throws for errors
        tools = await mcp_toolset.get_tools(readonly_context=None)
        
        if not tools:
            return [], {}
        
        function_declarations = []
        tool_map = {}  # Map tool names to MCPTool objects for execution
        
        for i, tool in enumerate(tools):
            # MCPTool has raw_mcp_tool which contains the actual MCP tool
            if not hasattr(tool, 'raw_mcp_tool'):
                continue
            raw_tool = tool.raw_mcp_tool
            
            # Check if raw_tool has inputSchema
            if hasattr(raw_tool, 'inputSchema'):
                # Build function declaration from MCP tool
                func_decl = FunctionDeclaration(
                    name=tool.name,
                    description=tool.description if hasattr(tool, 'description') else "",
                    parameters=raw_tool.inputSchema
                )
                function_declarations.append(func_decl)
                tool_map[tool.name] = tool  # Store the MCPTool object for later execution

        return function_declarations, tool_map

    async def execute_function_call(self, function_name, **kwargs) -> list:
        # Get the tool map
        _, tool_map = await self.mcp_toolset_to_function_declarations(self._toolset)
        
        # Get the MCPTool object for this function
        if function_name not in tool_map:
            raise ValueError(f"Tool {function_name} not found in tool map")
                            
        # Execute the tool directly with keyword arguments
        # MCPTool.run_async expects args and tool_context as keyword args
        mcp_tool = tool_map[function_name]
        return await mcp_tool.run_async(args=kwargs, tool_context=None)

    def stop(self):
        self._toolset = None
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
