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
from patch import patch_project, is_unified_diff
from sandbox_execution import execute_sandboxed
from pathlib import Path
from typing import Optional
import json
import logging

# Configure logging: all logs to file, only mcp_utils to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./solutions/mcp_server_debug.log')
    ]
)
logger = logging.getLogger(__name__)

# Add console handler specifically for mcp_utils
mcp_utils_logger = logging.getLogger('mcp_utils')
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
mcp_utils_logger.addHandler(console_handler)


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
        logger.info(f"list_files(pattern={pattern!r}) called")
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
        logger.info(f"load_file({file_path!r}) called")
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
        logger.info(f"create_file({file_path!r}, overwrite={overwrite}) called")
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
        logger.info(f"remove_file({file_path!r}) called")
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
        logger.info(f"get_line_range({file_path!r}, start_line={start_line}, end_line={end_line}) called")
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
        logger.info(f"search_files(pattern={pattern!r}, is_regex={is_regex}, case_sensitive={case_sensitive}, file_pattern={file_pattern!r}) called")
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
            def_type: Type of definition to find: 'class', 'def', 'method', or None for any
                     Use 'class' to find only classes
                     Use 'def' to find only functions/methods
                     Use 'method' to find only methods within classes
                     Use None (default) to find any type
        
        Returns:
            List of definitions containing:
            - type: 'class', 'function', or 'method'
            - name: name of the definition
            - file: relative file path
            - start_line and end_line: location in file
            - text: full source code of the definition
        """
        logger.info(f"find_python_definition(name={name!r}, def_type={def_type!r}) called")
        return pf.find_python_definition(name=name, def_type=def_type)
    
    # Expose patch_project as MCP tool
    @mcp.tool()
    def apply_patch(patch_content: str) -> dict:
        """
        Apply a unified diff patch to modify, create, or delete files in the project.
        
        IMPORTANT: This tool ONLY accepts patch_content parameter. Do not pass any other parameters.
        
        This tool automatically handles:
        - Modifying existing files (standard patch operation)
        - Creating new files (when patch shows --- /dev/null)
        - Deleting files (when patch shows +++ /dev/null)
        
        The patch must be in unified diff format with file markers (---, +++).
        Multiple files can be patched in a single operation.
        
        Args:
            patch_content: The ONLY parameter - unified diff patch as a string.
                          Must include --- and +++ markers for each file.
                          Example:
                          --- a/file.py
                          +++ b/file.py
                          @@ -1,3 +1,3 @@
                           line 1
                          -old line 2
                          +new line 2
                           line 3
        
        Returns:
            Dictionary with:
            - success: True if all hunks applied successfully
            - message: Summary of the operation
            - project_path: Path to the project
            
        Note: This is different from create_file. Use apply_patch for modifications via diff format.
        """
        try:
            patch_lines = patch_content.splitlines()
            
            # Check for unified diff format
            if not is_unified_diff(patch_lines):
                return {
                    "success": False,
                    "error": "Invalid patch format: not a valid unified diff",
                    "hint": "Use unified diff format with @@ hunk headers and file markers (--- and +++)",
                }
            
            project_dir = Path(pf.project_path)
                        
            # Apply patch and capture result
            failures = patch_project(project_dir, patch_lines, fuzziness=2)
            
            if failures:
                logger.error(f"Patch application failed - {len(failures)} file(s) had failures")
                failed_files = [f"{name}: {count} failed hunk(s)" for name, count in failures.items()]
                return {
                    "success": False,
                    "error": f"Patch application failed for {len(failures)} file(s)",
                    "failed_files": failed_files,
                    "hint": "Check that:\n1. File paths in patch match project structure\n2. Line numbers and context match current file content\n3. Files exist (or use /dev/null for new files)",
                    "project_path": str(project_dir)
                }
            
            logger.info("Patch applied successfully")
            return {
                "success": True,
                "message": "Patch applied successfully",
                "project_path": str(project_dir)
            }
            
        except ProjectFolderError as e:
            # These are validation errors from ProjectFolder
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation_error"
            }
        except Exception as e:
            # System errors - these are truly unexpected
            logger.exception("Unexpected error during patch application")
            raise ToolError(f"System error during patch application: {str(e)}")
    
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
        logger.info(f"execute_project(cmd_args={cmd_args!r}, timeout={timeout}) called")
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
        default="stdio",
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
