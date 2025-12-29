"""
FastMCP Server for File Operations

This module provides an MCP server that exposes file operations from mcp_utils
as tools for LLM agents. The server lifecycle is tied to the application.

Usage in your application:
    from mcp_server_file_ops import create_file_ops_server
    
    # Create server with your project path
    server = create_file_ops_server("/path/to/project")
    
    # Run in HTTP mode (for Gemini/Claude Desktop)
    server.run(transport="http", host="127.0.0.1", port=8000)
    
    # Or run in stdio mode (for direct integration)
    server.run(transport="stdio")

Author: Andrey Volkov
Date: December 28, 2025
"""

from fastmcp import FastMCP
from mcp_utils import ProjectFolder
from typing import Optional
import json


def create_file_ops_server(project_path: str, server_name: str = "file-operations") -> FastMCP:
    """
    Create a FastMCP server with file operation tools.
    
    Args:
        project_path: Path to the project folder to work with
        server_name: Name of the MCP server (default: "file-operations")
    
    Returns:
        FastMCP server instance ready to run
    """
    # Initialize MCP server
    mcp = FastMCP(server_name)
    
    # Initialize project folder
    pf = ProjectFolder(project_path)
    
    # Expose list_files as MCP tool
    @mcp.tool()
    def list_files(pattern: str = "*") -> str:
        """
        List all files in the project folder recursively.
        
        Args:
            pattern: Glob pattern for filtering files (default: "*" for all files)
                    Examples: "*.py" for Python files, "test_*.py" for test files
        
        Returns:
            JSON string with files list, each containing path, size in bytes and lines
        """
        result = pf.list_files(pattern=pattern)
        return json.dumps(result, indent=2)
    
    # Expose load_file as MCP tool
    @mcp.tool()
    def load_file(file_path: str) -> str:
        """
        Load and return the complete contents of a file.
        
        Args:
            file_path: Path to the file (relative to project folder)
                      Example: "src/main.py" or "subdir/file.txt"
        
        Returns:
            JSON string with file content and metadata (path, size)
        """
        result = pf.load_file(file_path)
        return json.dumps(result, indent=2)
    
    # Expose create_file as MCP tool
    @mcp.tool()
    def create_file(file_path: str, content: str) -> str:
        """
        Create a new file or overwrite existing file with given content.
        Parent directories are created automatically if needed.
        
        Args:
            file_path: Path to the file (relative to project folder)
            content: Content to write to the file
        
        Returns:
            JSON string with success status and file metadata
        """
        result = pf.create_file(file_path, content)
        return json.dumps(result, indent=2)
    
    # Expose remove_file as MCP tool
    @mcp.tool()
    def remove_file(file_path: str) -> str:
        """
        Remove a file from the project folder.
        
        Args:
            file_path: Path to the file to remove (relative to project folder)
        
        Returns:
            JSON string with success status
        """
        result = pf.remove_file(file_path)
        return json.dumps(result, indent=2)
    
    # Expose get_line_range as MCP tool
    @mcp.tool()
    def get_line_range(file_path: str, start_line: int, end_line: int) -> str:
        """
        Retrieve a specific range of lines from a file.
        
        Args:
            file_path: Path to the file (relative to project folder)
            start_line: Starting line number (1-indexed, inclusive)
            end_line: Ending line number (1-indexed, inclusive)
        
        Returns:
            JSON string with the requested lines and metadata
        """
        result = pf.get_line_range(file_path, start_line, end_line)
        return json.dumps(result, indent=2)
    
    # Expose search_files as MCP tool
    @mcp.tool()
    def search_files(
        pattern: str,
        is_regex: bool = False,
        case_sensitive: bool = True,
        file_pattern: str = "*"
    ) -> str:
        """
        Search for a string or regex pattern across all files in the project.
        
        Args:
            pattern: String or regex pattern to search for
            is_regex: If True, treat pattern as regex (default: False)
            case_sensitive: If True, search is case-sensitive (default: True)
            file_pattern: Glob pattern for which files to search (default: "*")
                         Examples: "*.py", "src/**/*.js"
        
        Returns:
            JSON string with list of matches containing file, line_number, and line content
        """
        result = pf.search_files(
            pattern=pattern,
            is_regex=is_regex,
            case_sensitive=case_sensitive,
            file_pattern=file_pattern
        )
        return json.dumps(result, indent=2)
    
    # Expose find_python_definition as MCP tool
    @mcp.tool()
    def find_python_definition(name: str, def_type: Optional[str] = None) -> str:
        """
        Find Python class or function/method definitions by name.
        
        Args:
            name: Name of the class, method, or function to find
            def_type: Type of definition to find: 'class', 'def', or None for both
                     Use 'class' to find only classes
                     Use 'def' to find only functions/methods
                     Use None (default) to find both
        
        Returns:
            JSON string with list of definitions containing:
            - type: 'class', 'function', or 'method'
            - name: name of the definition
            - file: relative file path
            - start_line and end_line: location in file
            - text: full source code of the definition
        """
        result = pf.find_python_definition(name=name, def_type=def_type)
        return json.dumps(result, indent=2)
    
    # Add a resource to expose project info
    @mcp.resource("project://info")
    def get_project_info() -> str:
        """Get information about the current project."""
        return json.dumps({
            "project_path": str(pf.project_path),
            "description": "File operations MCP server for coding agent project"
        }, indent=2)
    
    return mcp


# Standalone server for testing
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="FastMCP File Operations Server")
    parser.add_argument(
        "project_path",
        help="Path to the project folder"
    )
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default="http",
        help="Transport mode (default: http)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (http mode only, default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (http mode only, default: 8000)"
    )
    
    args = parser.parse_args()
    
    print(f"Starting FastMCP File Operations Server")
    print(f"Project Path: {args.project_path}")
    print(f"Transport: {args.transport}")
    
    # Create and run server
    server = create_file_ops_server(args.project_path)
    
    if args.transport == "http":
        print(f"HTTP Server: http://{args.host}:{args.port}")
        server.run(transport="http", host=args.host, port=args.port, path="/mcp")
    else:
        print("Running in stdio mode...")
        server.run(transport="stdio")
