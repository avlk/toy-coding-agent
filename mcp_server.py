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
from fastmcp.exceptions import ToolError
from mcp_utils import ProjectFolder, ProjectFolderError
from patch import patch_project
from sandbox_execution import execute_sandboxed
from pathlib import Path
from typing import Optional
import json


def create_file_ops_server(project_path: str, server_name: str = "file-operations", sandbox_method: str = "auto") -> FastMCP:
    """
    Create a FastMCP server with file operation tools.
    
    Args:
        project_path: Path to the project folder to work with
        server_name: Name of the MCP server (default: "file-operations")
        sandbox_method: Sandbox method for execute_project (default: "auto")
                       Options: 'auto', 'firejail', 'docker', 'bubblewrap', 'subprocess'
    
    Returns:
        FastMCP server instance ready to run
    """
    # Initialize MCP server
    mcp = FastMCP(server_name)
    
    # Initialize project folder
    pf = ProjectFolder(project_path)
    
    # Expose list_files as MCP tool
    @mcp.tool()
    def list_files(pattern: str = "*") -> list:
        """
        List all files in the project folder recursively.
        
        Args:
            pattern: Glob pattern for filtering files (default: "*" for all files)
                    Examples: "*.py" for Python files, "test_*.py" for test files
        
        Returns:
            List of file metadata dictionaries (path, size_bytes, size_lines, mtime)
        """
        return pf.list_files(pattern=pattern)
    
    # Expose load_file as MCP tool
    @mcp.tool()
    def load_file(file_path: str) -> dict:
        """
        Load and return the complete contents of a file.
        
        Args:
            file_path: Path to the file (relative to project folder)
                      Example: "src/main.py" or "subdir/file.txt"
        
        Returns:
            Dictionary with:
            - content: List of lines (line endings removed)
            - metadata: File metadata (path, size_bytes, size_lines, mtime)
        """
        return pf.load_file(file_path)
    
    # Expose create_file as MCP tool
    @mcp.tool()
    def create_file(file_path: str, content: str, overwrite: bool = False) -> dict:
        """
        Create a new file with given content.
        Fails if file already exists unless overwrite=True.
        Parent directories are created automatically if needed.
        
        Args:
            file_path: Path to the file (relative to project folder)
            content: Content to write - can be a string or list of lines (will be joined with newlines)
            overwrite: If True, overwrite existing file. If False, fail if file exists (default: False)
        
        Returns:
            Dictionary with file metadata (path, size_bytes, size_lines, mtime)
        """
        return pf.create_file(file_path, content, overwrite=overwrite)
    
    # Expose remove_file as MCP tool
    @mcp.tool()
    def remove_file(file_path: str) -> str:
        """
        Remove a file from the project folder.
        
        Args:
            file_path: Path to the file to remove (relative to project folder)
        
        Returns:
            Path of removed file
        """
        return pf.remove_file(file_path)
    
    # Expose get_line_range as MCP tool
    @mcp.tool()
    def get_line_range(file_path: str, start_line: int, end_line: int) -> dict:
        """
        Retrieve a specific range of lines from a file.
        
        Args:
            file_path: Path to the file (relative to project folder)
            start_line: Starting line number (1-indexed, inclusive)
            end_line: Ending line number (1-indexed, inclusive)
        
        Returns:
            Dictionary with the requested lines and metadata
        """
        return pf.get_line_range(file_path, start_line, end_line)
    
    # Expose search_files as MCP tool
    @mcp.tool()
    def search_files(
        pattern: str,
        is_regex: bool = False,
        case_sensitive: bool = True,
        file_pattern: str = "*"
    ) -> list:
        """
        Search for a string or regex pattern across all files in the project.
        
        Args:
            pattern: String or regex pattern to search for
            is_regex: If True, treat pattern as regex (default: False)
            case_sensitive: If True, search is case-sensitive (default: True)
            file_pattern: Glob pattern for which files to search (default: "*")
                         Examples: "*.py", "src/**/*.js"
        
        Returns:
            List of matches containing file, line_number, and line content
        """
        return pf.search_files(
            pattern=pattern,
            is_regex=is_regex,
            case_sensitive=case_sensitive,
            file_pattern=file_pattern
        )
    
    # Expose find_python_definition as MCP tool
    @mcp.tool()
    def find_python_definition(name: str, def_type: Optional[str] = None) -> list:
        """
        Find Python class or function/method definitions by name.
        
        Args:
            name: Name of the class, method, or function to find
            def_type: Type of definition to find: 'class', 'def', or None for both
                     Use 'class' to find only classes
                     Use 'def' to find only functions/methods
                     Use None (default) to find both
        
        Returns:
            List of definitions containing:
            - type: 'class', 'function', or 'method'
            - name: name of the definition
            - file: relative file path
            - start_line and end_line: location in file
            - text: full source code of the definition
        """
        return pf.find_python_definition(name=name, def_type=def_type)
    
    # Expose patch_project as MCP tool
    @mcp.tool()
    def apply_patch(patch_content: str, fuzziness: int = 0) -> dict:
        """
        Apply a unified diff patch to files in the project.
        
        This tool can:
        - Modify existing files
        - Create new files (when patch shows --- /dev/null)
        - Delete files (when patch shows +++ /dev/null)
        
        The patch must be in unified diff format with file markers (---, +++).
        Multiple files can be patched in a single operation.
        
        Args:
            patch_content: The unified diff patch as a string
                          Should include --- and +++ markers for each file
                          Example:
                          --- a/file.py
                          +++ b/file.py
                          @@ -1,3 +1,3 @@
                           line 1
                          -old line 2
                          +new line 2
                           line 3
            fuzziness: Level of fuzzy matching (0-2, default: 0)
                      0 = exact match required
                      1 = ignore whitespace and comments
                      2 = allow small character differences (Levenshtein distance <= 3)
        
        Returns:
            Dictionary with:
            - success: True if all hunks applied successfully
            - message: Summary of the operation
            - details: Information about processed files and hunks
        """
        try:
            patch_lines = patch_content.splitlines()
            project_dir = Path(pf.project_path)
            
            # Apply patch and capture result
            success = patch_project(project_dir, patch_lines, fuzziness=fuzziness)
            
            if not success:
                raise ToolError("Patch application failed")
            
            return {
                "success": True,
                "message": "Patch applied successfully",
                "project_path": str(project_dir)
            }
            
        except ProjectFolderError:
            raise
        except Exception as e:
            raise ToolError(f"Exception occurred during patch application: {str(e)}")
    
    # Expose execute_sandboxed as MCP tool
    @mcp.tool()
    def execute_project(cmd_args: str, timeout: int = 30) -> dict:
        """
        Execute a Python project with sandboxing.
        
        The project folder is the current project folder configured for this server.
        A virtual environment (.venv) will be automatically created if it doesn't exist,
        and any requirements.txt file will be automatically installed.
        
        Args:
            cmd_args: Command with entry point and arguments
                     Example: "main.py --verbose arg1 arg2"
                     Example: "script.py"
            timeout: Execution timeout in seconds (default: 30)
        
        Returns:
            Dictionary with:
            - success: True if execution succeeded (exit code 0)
            - stdout: Standard output from the execution
            - stderr: Standard error from the execution
            - exit_code: Process exit code
        
        Project structure expected:
            project/
            ├── main.py           # or other entry point
            ├── module1.py        # additional modules
            ├── .venv/            # auto-created if doesn't exist
            └── requirements.txt  # optional, auto-installed if present
        """
        try:
            result = execute_sandboxed(
                project=str(pf.project_path),
                cmd_args=cmd_args,
                timeout=timeout,
                method=sandbox_method
            )
            # execute_sandboxed returns dict with success, stdout, stderr, exit_code
            return result
        except Exception as e:
            raise ToolError(f"Execution failed: {str(e)}")
    
    # Add a resource to expose project info
    @mcp.resource("project://info")
    def get_project_info() -> dict:
        """Get information about the current project."""
        return {
            "project_path": str(pf.project_path),
            "description": "File operations MCP server for coding agent project"
        }
    
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
