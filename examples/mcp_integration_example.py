"""
Example: Integrating File Operations MCP Server with Coding Agent

This demonstrates three ways to integrate the MCP server:
1. In-process integration (recommended for same application)
2. HTTP server mode (for remote/separate process)
3. Stdio mode (for Claude Desktop / direct pipe)

Author: Andrey Volkov
Date: December 28, 2025
"""

import threading
import time
import sys
from pathlib import Path
from google import genai
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the MCP server
from mcp_server_file_ops import create_file_ops_server


# ============================================================================
# Option 1: In-Process Integration (Recommended)
# ============================================================================
# The MCP server runs in the same process as your application.
# Most efficient for single application use.

def example_in_process_integration():
    """
    Example: Use MCP server directly in your application.
    This is the simplest approach when everything runs in one process.
    """
    print("=== In-Process Integration Example ===\n")
    
    # Your application's project path
    project_path = "/home/volkov/tests/coding-agent/solutions"
    
    # Create the MCP server (doesn't start networking, just registers tools)
    mcp_server = create_file_ops_server(project_path)
    
    print(f"✓ MCP Server created for: {project_path}")
    print(f"✓ Available tools: {len(mcp_server._tools)} registered")
    print("\nTools available:")
    for tool_name in mcp_server._tools.keys():
        print(f"  - {tool_name}")
    
    # The server is now ready - tools are registered and can be called
    # You can directly call tools if needed:
    # result = mcp_server._tools['list_files'].fn(pattern="*.py")
    
    return mcp_server


# ============================================================================
# Option 2: HTTP Server Mode (For Remote Access or Testing)
# ============================================================================
# Run the MCP server as HTTP endpoint, useful for:
# - Testing with tools like curl
# - Remote access from other machines
# - Integration with web-based tools

def example_http_server_mode():
    """
    Example: Run MCP server as HTTP service in background thread.
    Useful for remote access or when you want HTTP-based communication.
    """
    print("\n=== HTTP Server Mode Example ===\n")
    
    project_path = "/home/volkov/tests/coding-agent/solutions"
    
    # Create server
    mcp_server = create_file_ops_server(project_path)
    
    # Run server in background thread
    def run_server():
        print("Starting HTTP server on http://127.0.0.1:8000")
        mcp_server.run(transport="http", host="127.0.0.1", port=8000)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("✓ HTTP MCP Server started in background")
    print("✓ Access at: http://127.0.0.1:8000")
    print("✓ Try: curl http://127.0.0.1:8000/tools")
    
    # Your application continues running...
    # The server runs in the background
    
    return mcp_server, server_thread


# ============================================================================
# Option 3: Integration with Gemini Agent
# ============================================================================
# Use the MCP tools with Google's Gemini models

def example_gemini_integration():
    """
    Example: Use MCP file operations with Gemini.
    
    Note: As of Dec 2025, Gemini doesn't natively support MCP protocol.
    But you can wrap MCP tools as Gemini function calls.
    """
    print("\n=== Gemini Integration Example ===\n")
    
    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠ GEMINI_API_KEY not set, skipping Gemini example")
        return None
    
    project_path = "/home/volkov/tests/coding-agent/solutions"
    
    # Create MCP server (for tool definitions)
    mcp_server = create_file_ops_server(project_path)
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    
    print("✓ MCP Server tools available for Gemini")
    print("✓ You can wrap MCP tools as Gemini functions")
    
    # Example: Convert MCP tool to Gemini function declaration
    # (You would need to create proper Gemini function schema)
    
    # Example query to Gemini with file operations context
    example_query = """
    I need to analyze Python files in the project. 
    Please list all Python files and then read the main file.
    """
    
    print(f"\nExample query: {example_query}")
    print("\nIn a real integration, you would:")
    print("1. Convert MCP tool schemas to Gemini function declarations")
    print("2. Register them with genai.types.Tool")
    print("3. Let Gemini call the functions")
    print("4. Execute the MCP tools and return results to Gemini")
    
    return mcp_server, client


# ============================================================================
# Option 4: Complete Application Integration Pattern
# ============================================================================

class CodingAgentWithMCP:
    """
    Example: Full integration pattern for your coding agent.
    The MCP server lifecycle is tied to the application.
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.mcp_server = None
        self.is_running = False
        
        # Initialize MCP server
        self._init_mcp_server()
    
    def _init_mcp_server(self):
        """Initialize MCP server for file operations."""
        print(f"Initializing MCP server for: {self.project_path}")
        self.mcp_server = create_file_ops_server(self.project_path)
        print(f"✓ MCP server ready with {len(self.mcp_server._tools)} tools")
    
    def start(self):
        """Start the coding agent and MCP server."""
        print("\n=== Starting Coding Agent with MCP ===")
        self.is_running = True
        
        # If you want HTTP access, start server in background
        # self.server_thread = threading.Thread(
        #     target=lambda: self.mcp_server.run(transport="http", port=8000),
        #     daemon=True
        # )
        # self.server_thread.start()
        
        print("✓ Agent started")
        print("✓ MCP tools available for use")
        
        # Your agent logic here...
    
    def stop(self):
        """Stop the coding agent and MCP server."""
        print("\n=== Stopping Coding Agent ===")
        self.is_running = False
        # MCP server will stop when threads stop (daemon threads)
        print("✓ Agent stopped")
    
    def get_tool(self, tool_name: str):
        """Get a specific MCP tool by name."""
        return self.mcp_server._tools.get(tool_name)
    
    def list_available_tools(self):
        """List all available MCP tools."""
        return list(self.mcp_server._tools.keys())


# ============================================================================
# Main Example Runner
# ============================================================================

def main():
    """Run all integration examples."""
    
    print("=" * 70)
    print("FastMCP File Operations Integration Examples")
    print("=" * 70)
    
    # Example 1: In-process (recommended)
    mcp1 = example_in_process_integration()
    
    # Example 2: HTTP server mode
    # Uncomment to test HTTP mode
    # mcp2, thread2 = example_http_server_mode()
    # time.sleep(2)  # Let server start
    
    # Example 3: Gemini integration
    example_gemini_integration()
    
    # Example 4: Full application pattern
    print("\n" + "=" * 70)
    print("Complete Application Pattern")
    print("=" * 70)
    
    # Create agent with integrated MCP
    agent = CodingAgentWithMCP("/home/volkov/tests/coding-agent/solutions")
    agent.start()
    
    # List available tools
    print("\nAvailable MCP tools:")
    for tool in agent.list_available_tools():
        print(f"  - {tool}")
    
    # Example: Use a tool directly
    list_files_tool = agent.get_tool('list_files')
    if list_files_tool:
        print("\nExample: Calling list_files tool...")
        result = list_files_tool.fn(pattern="*.py")
        print(result[:200] + "..." if len(result) > 200 else result)
    
    # Simulate some work
    print("\nAgent running... (press Ctrl+C to stop)")
    
    try:
        time.sleep(2)  # Simulate work
    except KeyboardInterrupt:
        pass
    
    # Stop agent (MCP server lifecycle ends with application)
    agent.stop()
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nRecommended approach for your use case:")
    print("  1. Use in-process integration (Option 1 / Option 4)")
    print("  2. Initialize MCP server when your application starts")
    print("  3. Tools are available throughout application lifetime")
    print("  4. MCP server stops when application stops")
    print("\nFor Gemini integration:")
    print("  - Convert MCP tool schemas to Gemini function declarations")
    print("  - Register with genai.types.Tool in your config")
    print("  - Call MCP tools when Gemini requests them")


if __name__ == "__main__":
    main()
