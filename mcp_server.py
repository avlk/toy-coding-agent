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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./solutions/mcp_server_debug.log')
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add console handler specifically for mcp_utils
mcp_utils_logger = logging.getLogger('mcp_utils')
mcp_utils_logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
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
    @mcp.tool(annotations={"readOnlyHint": True})
    def list_files(pattern: str = "*") -> dict:
        """
        List all files in the project folder recursively.
        
        Args:
            pattern: Glob pattern for filtering files (default: "*" for all files)
                    Examples: "*.py" for Python files, "test_*.py" for test files
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - files: List of file metadata dictionaries (only present if success=True)
            - error: Error message (only present if success=False)
        """
        logger.info(f"list_files(pattern={pattern!r}) called")
        try:
            files = pf.list_files(pattern=pattern)
            return {
                'success': True,
                'files': files
            }
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose load_file as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
    def load_file(file_path: str) -> dict:
        """
        Load and return the complete contents of a file.
        
        Args:
            file_path: Path to the file (relative to project folder)
                      Example: "src/main.py" or "subdir/file.txt"
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - content: List of lines (line endings removed, only present if success=True)
            - metadata: File metadata (only present if success=True)
            - error: Error message (only present if success=False)
        """
        logger.info(f"load_file({file_path!r}) called")
        try:
            result = pf.load_file(file_path)
            result['success'] = True
            return result
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
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
            Dictionary with:
                - success: Operation success status. True for successful creation/update
                - message: Description of the result
                - metadata: File metadata (only present when file was created/updated)
                - error: Error message (only present if success=False)
        
        Special case - no_change:
            When overwrite=True and new content is identical to existing file, returns:
            - success: True (operation completed successfully)
            - message: 'File content unchanged'
            - metadata: Current file metadata
            
            ⚠️ CRITICAL: If you get 'no_change', your intended changes didn't apply!
            Your new content matched the existing file exactly.
            To fix: 1) load_file() to see current content
                   2) Understand what you actually wanted to change
                   3) Create corrected content
                   4) Retry with correct changes
        """
        logger.info(f"create_file({file_path!r}, overwrite={overwrite}) called")
        result = pf.create_file(file_path, content, overwrite=overwrite)
        
        # Convert 'status' to 'success' for consistency
        status = result.pop('status')
        result['success'] = (status == 'success')
        
        # If status was 'no_change', still return success=True but keep message
        if status == 'no_change':
            result['success'] = True
        
        # If status was 'error', ensure error field exists
        if status == 'error' and 'error' not in result:
            result['error'] = result.get('message', 'Unknown error')
        
        # Log the result status
        if not result['success']:
            logger.error(f"create_file failed: {result.get('message', result.get('error'))}")
        elif status == 'no_change':
            logger.warning(f"create_file no change: {result['message']}")
        
        return result
    
    # Expose remove_file as MCP tool
    @mcp.tool(annotations={"destructiveHint": True})
    def remove_file(file_path: str) -> dict:
        """
        Remove a file from the project folder.
        
        Args:
            file_path: Path to the file to remove (relative to project folder)
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - path: Path of removed file (only present if success=True)
            - error: Error message (only present if success=False)
        """
        logger.info(f"remove_file({file_path!r}) called")
        try:
            path = pf.remove_file(file_path)
            return {
                'success': True,
                'path': path
            }
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose get_line_range as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
    def get_line_range(file_path: str, start_line: int, end_line: int) -> dict:
        """
        Retrieve a specific range of lines from a file.
        
        Args:
            file_path: Path to the file (relative to project folder)
            start_line: Starting line number (1-indexed, inclusive)
            end_line: Ending line number (1-indexed, inclusive)
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - lines: Requested lines (only present if success=True)
            - metadata: File metadata (only present if success=True)
            - error: Error message (only present if success=False)
        """
        logger.info(f"get_line_range({file_path!r}, start_line={start_line}, end_line={end_line}) called")
        try:
            result = pf.get_line_range(file_path, start_line, end_line)
            result['success'] = True
            return result
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose search_files as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
    def search_files(
        pattern: str,
        is_regex: bool = False,
        case_sensitive: bool = True,
        file_pattern: str = "*"
    ) -> dict:
        """
        Search for a string or regex pattern across all files in the project.
        
        Args:
            pattern: String or regex pattern to search for
            is_regex: If True, treat pattern as regex (default: False)
            case_sensitive: If True, search is case-sensitive (default: True)
            file_pattern: Glob pattern for which files to search (default: "*")
                         Examples: "*.py", "src/**/*.js"
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - matches: List of matches containing file, line_number, and line content (only present if success=True)
            - error: Error message (only present if success=False)
        """
        logger.info(f"search_files(pattern={pattern!r}, is_regex={is_regex}, case_sensitive={case_sensitive}, file_pattern={file_pattern!r}) called")
        try:
            matches = pf.search_files(
                pattern=pattern,
                is_regex=is_regex,
                case_sensitive=case_sensitive,
                file_pattern=file_pattern
            )
            return {
                'success': True,
                'matches': matches
            }
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose find_python_definition as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
    def find_python_definition(name: str, def_type: Optional[str] = None) -> dict:
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
            Dictionary with:
            - success: Operation success status (always True unless error)
            - definitions: List of definitions containing:
                - type: 'class', 'function', or 'method'
                - name: name of the definition
                - file: relative file path
                - start_line and end_line: location in file
                - text: full source code of the definition
            - error: Error message (only present if success=False)
        """
        logger.info(f"find_python_definition(name={name!r}, def_type={def_type!r}) called")
        try:
            definitions = pf.find_python_definition(name=name, def_type=def_type)
            return {
                'success': True,
                'definitions': definitions
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose run_ruff_check as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
    def run_ruff_check(file_pattern: str = "**/*.py", fix: bool = False) -> dict:
        """
        Run Ruff linter on project files and return structured linting results.
        
        Analyzes Python files for code quality issues, style violations, and potential bugs.
        Requires Ruff to be installed and available in PATH.
        
        Args:
            file_pattern: Glob pattern for files to check (default: "**/*.py")
                         Examples: "**/*.py" (all Python files), "src/**/*.py" (only src folder)
            fix: If True, automatically fix fixable issues (default: False)
                WARNING: Enabling fix will modify files directly
        
        Returns:
            Dictionary with:
            - success: Operation success status - False if issues found or execution failed, True only if no issues
            - issues: List of issue dictionaries, each containing:
                - file: Relative file path
                - line: Line number (1-indexed)
                - column: Column number (1-indexed)
                - code: Rule code (e.g., "F401" for unused import, "E501" for line too long)
                - message: Human-readable description of the issue
                - fixable: Boolean indicating if issue can be auto-fixed
            - total_issues: Total number of issues found across all files
            - total_files: Number of files containing at least one issue
            - error: Error message (present if success=False)
        
        Note:
            Returns success=False when ANY linting issues are found (this is by design).
            Returns success=True only when project has zero issues.
            Check 'issues' list for details even when success=False.
            Returns success=False with specific error when Ruff execution fails (e.g., not installed).
        
        Common rule codes:
        - F401: Unused import
        - F841: Unused variable
        - E501: Line too long
        - W291: Trailing whitespace
        """
        logger.info(f"run_ruff_check(file_pattern={file_pattern!r}, fix={fix!r}) called")
        return pf.run_ruff_check(file_pattern=file_pattern, fix=fix)
    
    # Expose create_snapshot as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
    def create_snapshot(label: Optional[str] = None) -> dict:
        """
        Create a snapshot of the current project state.
        
        A snapshot captures the current state of all code files and checklists,
        storing them with a unique ID for later restoration. Excluded files 
        (like .venv, __pycache__) are not included in snapshots.
        
        💡 Best practice: Create a snapshot at the START of each implementation iteration
        before making any changes, so you can revert if needed.
        
        Args:
            label: Optional descriptive label for the snapshot (default: auto-generated with timestamp)
                   Example: "Before refactoring", "Working version 1.0"
        
        Returns:
            Dictionary with:
            - success: Operation success status (always True unless error)
            - snapshot_id: Unique ID of the created snapshot (sequential number: "1", "2", etc.)
            - error: Error message (only present if success=False)
        
        Use cases:
        - Save state before major refactoring
        - Create checkpoints during development
        - Preserve working versions before experiments
        """
        logger.info(f"create_snapshot(label={label!r}) called")
        try:
            snapshot_id = pf.create_snapshot(label=label)
            return {
                'success': True,
                'snapshot_id': snapshot_id
            }
        except Exception as e:
            logger.error(f"create_snapshot failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose list_snapshots as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
    def list_snapshots() -> dict:
        """
        List all available snapshots with their metadata.
        
        Returns a list of all snapshots in chronological order (oldest to newest),
        including their IDs, timestamps, and labels.
        
        Returns:
            Dictionary with:
            - success: Operation success status (always True unless error)
            - snapshots: List of snapshot dictionaries, each containing:
                - id: Snapshot ID (string)
                - timestamp: ISO formatted creation timestamp
                - label: Descriptive label
            - count: Total number of snapshots
            - error: Error message (only present if success=False)
        
        Use cases:
        - View available restore points
        - Check snapshot history
        - Find specific snapshot by label
        """
        logger.info("list_snapshots() called")
        try:
            snapshots = pf.list_snapshots()
            return {
                'success': True,
                'snapshots': snapshots,
                'count': len(snapshots)
            }
        except Exception as e:
            logger.error(f"list_snapshots failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose restore_snapshot as MCP tool
    @mcp.tool(annotations={"destructiveHint": True})
    def restore_snapshot(snapshot_id: str) -> dict:
        """
        Restore the project to a previous snapshot state.
        
        This operation restores all code files and checklists to the state
        captured in the specified snapshot. 
        
        Args:
            snapshot_id: ID of the snapshot to restore (obtained from list_snapshots)
                        Example: "1", "2", "3"
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - snapshot_id: ID of the restored snapshot
            - error: Error message (only present if success=False)
        
        Use cases:
        - Revert to a previous working state
        - Undo failed experiments
        - Switch between different code versions
        
        Note: Create a snapshot of current state before restoring if you want to preserve it.
        """
        logger.info(f"restore_snapshot(snapshot_id={snapshot_id!r}) called")
        try:
            result = pf.restore_snapshot(snapshot_id)
            
            if result:
                return {
                    'success': True,
                    'snapshot_id': snapshot_id
                }
            else:
                return {
                    'success': False,
                    'error': f"Snapshot {snapshot_id} not found"
                }
        except Exception as e:
            logger.error(f"restore_snapshot failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Do not expose patch_project as MCP tool for a while
    # @mcp.tool(annotations={"destructiveHint": True})
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
            - error: Error message (only present if success=False)
            - failed_files: List of files that failed to apply with number of failed hunks (only present if success=False)
            - hint: Message for troubleshooting (only present if success=False)
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
    
    # Expose replace_in_files as MCP tool
    @mcp.tool(annotations={"destructiveHint": True})
    def replace_in_files(
        pattern: str,
        replacement: str,
        is_regex: bool = False,
        file_pattern: str = "*"
    ) -> dict:
        """
        Search and replace a pattern across all matching files.
        
        For each file that matches the file_pattern, loads the file,
        performs pattern replacement, and saves it if any replacements were made.
        
        Note: Returns success=False if no matches found (even though operation executed correctly).
        Check the 'replacements' dict to see which files were modified and counts.
        
        Args:
            pattern: String or regex pattern to search for
            replacement: String to replace matches with
            is_regex: If True, treat pattern as regex (default: False)
                     When True, replacement can use backreferences (\1, \2, etc.)
            file_pattern: Glob pattern for filtering which files to process (default: "*")
                         Examples: "*.py", "src/**/*.py"
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - replacements: Dictionary mapping relative file path to number of replacements made
            - error: Error message (only present if success=False)
        """
        logger.info(f"replace_in_files(pattern={pattern!r}, replacement={replacement!r}, is_regex={is_regex}, file_pattern={file_pattern!r}) called")
        try:
            replacements = pf.replace_in_files(pattern, replacement, is_regex, file_pattern)
            total_replacements = sum(replacements.values())
            
            if total_replacements == 0:
                return {
                    'success': False,
                    'error': 'No matches found for the pattern',
                    'replacements': replacements
                }
            
            return {
                'success': True,
                'replacements': replacements
            }
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose multiline_replace_in_file as MCP tool
    @mcp.tool(annotations={"destructiveHint": True})
    def multiline_replace_in_file(
        file_path: str,
        search_lines: list[str],
        replace_lines: list[str],
        only_around_line: Optional[int] = None
    ) -> dict:
        """
        Search and replace a multiline pattern in a specific file.
        
        Loads the file, performs multiline replacement, and saves it if any
        replacements were made.
        
        Args:
            file_path: Relative path to the file (relative to project folder)
            search_lines: List of lines to search for (must match exactly)
                         ⚠️ CRITICAL: Pass ["line1", "line2"], NOT "line1\nline2"
                         Each line is a separate string in the list
            replace_lines: List of lines to replace with
                          ⚠️ CRITICAL: Pass ["line1", "line2"], NOT "line1\nline2"
                          Each line is a separate string in the list
            only_around_line: If not None, only replace the match closest to this line number (1-indexed)
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - replacements: Number of replacement operations performed
            - error: Error message (only present if success=False)
        """
        logger.info(f"multiline_replace_in_file(file_path={file_path!r}, search_lines={len(search_lines)} lines, replace_lines={len(replace_lines)} lines, only_around_line={only_around_line}) called")
        
        # Log exact search strings for debugging
        for i, line in enumerate(search_lines):
            logger.debug(f"search_lines[{i}] = {line!r}")
        
        try:
            replacements = pf.multiline_replace_in_file(file_path, search_lines, replace_lines, only_around_line)
            if replacements == 0:
                error_details = "No matches found. Check that search_lines is a list of exact lines to match. Do not format, adjust or escape them in any way."
                
                return {
                    'success': False,
                    'error': error_details,
                    'replacements': replacements
                }
            else:
                return {
                    'success': True,
                    'replacements': replacements
                }
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose fuzzy_replace_in_file as MCP tool
    @mcp.tool(annotations={"destructiveHint": True})
    def fuzzy_replace_in_file(
        file_path: str,
        search_lines: list[str],
        replace_lines: list[str],
        around_line: int
    ) -> dict:
        """
        Search and replace a multiline pattern in a specific file using fuzzy matching.
        
        This tool finds the closest approximate match to the search pattern near the
        specified line and replaces it. Allows for small differences (typos, spacing,
        minor edits) between the search pattern and actual code.
        
        Use this when:
        - The exact code structure is slightly different than expected
        - There might be minor whitespace differences
        - You want to replace code near a specific line even if not an exact match
        
        ⚠️ CRITICAL LIMITATIONS:
        - Avoid calling this multiple times on the same file in one iteration
        - After first replacement, around_line offsets change, causing subsequent calls to fail
        - For multiple edits in same file: use multiline_replace_in_file or replace_in_files instead
        
        Args:
            file_path: Relative path to the file (relative to project folder)
            search_lines: List of lines to search for (approximate match allowed, small differences OK)
                         ⚠️ CRITICAL: Pass ["line1", "line2"], NOT "line1\nline2"
                         Each line is a separate string in the list
            replace_lines: List of lines to replace with
                          ⚠️ CRITICAL: Pass ["line1", "line2"], NOT "line1\nline2"
                          Each line is a separate string in the list
            around_line: Line number around which to search for the match (1-indexed, required)
        
        Returns:
            Dictionary with:
            - success: Operation success status
            - matched_line: Actual line number where replacement was made (only present if success=True)
            - error: Error message (only present if success=False)
        """
        logger.info(f"fuzzy_replace_in_file(file_path={file_path!r}, search_lines={len(search_lines)} lines, replace_lines={len(replace_lines)} lines, around_line={around_line}) called")
        
        # Log exact search strings for debugging
        for i, line in enumerate(search_lines):
            logger.debug(f"search_lines[{i}] = {line!r}")
        
        try:
            message, matched_line = pf.fuzzy_replace_in_file(file_path, search_lines, replace_lines, around_line)
            if matched_line is None:
                error_details = message
                
                return {
                    'success': False,
                    'error': error_details
                }
            else:
                return {
                    'success': True,
                    'matched_line': matched_line
                }
        except ProjectFolderError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Expose execute_sandboxed as MCP tool
    @mcp.tool(annotations={"readOnlyHint": True})
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
                project=str(project_path + "/current/code"),
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
