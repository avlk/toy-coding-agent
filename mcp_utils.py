"""
MCP Utilities for Project File Operations

This module provides a secure set of file operations for working with files
in a specified project folder. All operations are restricted to the project
folder to prevent path traversal attacks.

Functionality:
- List files with metadata (size in bytes and lines)
- Load and retrieve file contents
- Create and remove files
- Retrieve specific line ranges from files
- Search for strings/regex across files
- Find and extract Python class/method definitions

All functions return JSON-serializable dictionaries for easy MCP integration.

Author: Andrey Volkov
Date: December 28, 2025
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any


class ProjectFolderError(Exception):
    """Custom exception for project folder operations."""
    pass


class ProjectFolder:
    """
    Manages file operations within a specified project folder.
    
    All file paths are validated to ensure they remain within the project
    folder, preventing path traversal attacks.
    
    Attributes:
        project_path: Absolute path to the project folder
        _line_count_cache: Cache for file line counts with modification times
    """
    
    def __init__(self, project_path: str):
        """
        Initialize ProjectFolder with a project directory.
        
        Args:
            project_path: Path to the project folder (relative or absolute)
            
        Raises:
            ProjectFolderError: If the project path doesn't exist or isn't a directory
        """
        self.project_path = Path(project_path).resolve()
        
        if not self.project_path.exists():
            raise ProjectFolderError(f"Project path does not exist: {project_path}")
        
        if not self.project_path.is_dir():
            raise ProjectFolderError(f"Project path is not a directory: {project_path}")
        
        # Cache structure: {absolute_path_str: (mtime, line_count)}
        self._line_count_cache: Dict[str, Tuple[float, int]] = {}
    
    def _validate_path(self, file_path: Union[str, Path]) -> Path:
        """
        Validate that a file path is within the project folder.
        
        Args:
            file_path: Relative or absolute path to validate
            
        Returns:
            Absolute Path object within the project folder
            
        Raises:
            ProjectFolderError: If path is outside the project folder
        """
        # Convert to Path and resolve to absolute path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        # If relative, make it relative to project folder
        if not file_path.is_absolute():
            full_path = (self.project_path / file_path).resolve()
        else:
            full_path = file_path.resolve()
        
        # Check if the path is within project folder
        try:
            full_path.relative_to(self.project_path)
        except ValueError:
            raise ProjectFolderError(
                f"Path '{file_path}' is outside the project folder '{self.project_path}'"
            )
        
        return full_path
    
    def _get_line_count(self, file_path: Path) -> int:
        """
        Get line count for a file, using cache if possible.
        
        Args:
            file_path: Absolute path to the file
            
        Returns:
            Number of lines in the file
        """
        try:
            stat_info = os.stat(file_path)
            mtime = stat_info.st_mtime
            path_str = str(file_path)
            
            # Check cache
            if path_str in self._line_count_cache:
                cached_mtime, cached_count = self._line_count_cache[path_str]
                if cached_mtime == mtime:
                    return cached_count
            
            # Count lines
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            
            # Update cache
            self._line_count_cache[path_str] = (mtime, line_count)
            
            return line_count
        except Exception:
            # If we can't read the file, return 0
            return 0
    
    def _get_indentation(self, line: str) -> int:
        """
        Get the indentation level of a line (number of leading spaces).
        
        Args:
            line: Line of text
            
        Returns:
            Number of leading spaces (tabs count as 4 spaces)
        """
        indent = 0
        for char in line:
            if char == ' ':
                indent += 1
            elif char == '\t':
                indent += 4
            else:
                break
        return indent
    
    def _find_def_end(self, lines: List[str], start_idx: int, start_indent: int) -> int:
        """
        Find the end line of a Python definition block using indentation.
        
        Args:
            lines: List of all lines in the file
            start_idx: Starting line index (0-based)
            start_indent: Indentation level of the definition line
            
        Returns:
            End line index (0-based, inclusive)
        """
        end_idx = start_idx
        
        # Skip the definition line itself
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                end_idx = i
                continue
            
            # Check indentation
            indent = self._get_indentation(line)
            
            # If indentation is less than or equal to start, we've exited the block
            if indent <= start_indent:
                break
            
            end_idx = i
        
        return end_idx
    
    def _error_response(self, error: str, **kwargs) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            error: Error message
            **kwargs: Additional fields to include
            
        Returns:
            Error response dictionary
        """
        response = {
            'success': False,
            'error': error
        }
        response.update(kwargs)
        return response
    
    def _success_response(self, **kwargs) -> Dict[str, Any]:
        """
        Create a standardized success response.
        
        Args:
            **kwargs: Fields to include in the response
            
        Returns:
            Success response dictionary
        """
        response = {'success': True}
        response.update(kwargs)
        return response
    
    def _file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Get metadata for a file.
        
        Args:
            file_path: Absolute path to the file
            
        Returns:
            Dictionary with file metadata
        """
        try:
            stat_info = os.stat(file_path)
            rel_path = file_path.relative_to(self.project_path)
            
            return {
                'path': str(rel_path),
                'absolute_path': str(file_path),
                'size_bytes': stat_info.st_size,
                'size_lines': self._get_line_count(file_path)
            }
        except Exception as e:
            return {
                'path': str(file_path.relative_to(self.project_path)),
                'error': str(e)
            }
    
    def list_files(self, pattern: str = "*") -> Dict[str, Any]:
        """
        List all files in the project folder recursively.
        
        Args:
            pattern: Glob pattern for filtering files (default: "*" for all files)
            
        Returns:
            Dictionary with:
                - success: True if operation succeeded
                - files: List of file metadata dictionaries
                - count: Total number of files
                - error: Error message if failed
        """
        try:
            files = []
            
            # Use rglob for recursive search
            for file_path in self.project_path.rglob(pattern):
                if file_path.is_file():
                    files.append(self._file_metadata(file_path))
            
            # Sort by path for consistent output
            files.sort(key=lambda x: x['path'])
            
            return self._success_response(files=files, count=len(files))
        
        except Exception as e:
            return self._error_response(f"Failed to list files: {str(e)}")
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and return the complete contents of a file.
        
        Args:
            file_path: Path to the file (relative to project folder or absolute)
            
        Returns:
            Dictionary with:
                - success: True if operation succeeded
                - content: File contents as string
                - metadata: File metadata
                - error: Error message if failed
        """
        try:
            full_path = self._validate_path(file_path)
            
            if not full_path.exists():
                return self._error_response(f"File not found: {file_path}")
            
            if not full_path.is_file():
                return self._error_response(f"Path is not a file: {file_path}")
            
            # Try to read as text
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with error handling for binary files
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            metadata = self._file_metadata(full_path)
            
            return self._success_response(content=content, metadata=metadata)
        
        except ProjectFolderError as e:
            return self._error_response(str(e))
        except PermissionError:
            return self._error_response(f"Permission denied: {file_path}")
        except Exception as e:
            return self._error_response(f"Failed to load file: {str(e)}")
    
    def create_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Create a new file with the given content.
        
        Args:
            file_path: Path to the file (relative to project folder or absolute)
            content: Content to write to the file
            
        Returns:
            Dictionary with:
                - success: True if operation succeeded
                - metadata: File metadata
                - error: Error message if failed
        """
        try:
            full_path = self._validate_path(file_path)
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Clear cache for this file
            path_str = str(full_path)
            if path_str in self._line_count_cache:
                del self._line_count_cache[path_str]
            
            metadata = self._file_metadata(full_path)
            
            return self._success_response(metadata=metadata)
        
        except ProjectFolderError as e:
            return self._error_response(str(e))
        except PermissionError:
            return self._error_response(f"Permission denied: {file_path}")
        except Exception as e:
            return self._error_response(f"Failed to create file: {str(e)}")
    
    def remove_file(self, file_path: str) -> Dict[str, Any]:
        """
        Remove a file from the project folder.
        
        Args:
            file_path: Path to the file (relative to project folder or absolute)
            
        Returns:
            Dictionary with:
                - success: True if operation succeeded
                - path: Path of the removed file
                - error: Error message if failed
        """
        try:
            full_path = self._validate_path(file_path)
            
            if not full_path.exists():
                return self._error_response(f"File not found: {file_path}")
            
            if not full_path.is_file():
                return self._error_response(f"Path is not a file: {file_path}")
            
            # Get relative path before deletion
            rel_path = str(full_path.relative_to(self.project_path))
            
            # Remove from cache
            path_str = str(full_path)
            if path_str in self._line_count_cache:
                del self._line_count_cache[path_str]
            
            # Delete the file
            full_path.unlink()
            
            return self._success_response(path=rel_path)
        
        except ProjectFolderError as e:
            return self._error_response(str(e))
        except PermissionError:
            return self._error_response(f"Permission denied: {file_path}")
        except Exception as e:
            return self._error_response(f"Failed to remove file: {str(e)}")
    
    def get_line_range(self, file_path: str, start_line: int, end_line: int) -> Dict[str, Any]:
        """
        Retrieve a specific range of lines from a file.
        
        Args:
            file_path: Path to the file (relative to project folder or absolute)
            start_line: Starting line number (1-indexed, inclusive)
            end_line: Ending line number (1-indexed, inclusive)
            
        Returns:
            Dictionary with:
                - success: True if operation succeeded
                - lines: List of lines in the range
                - start_line: Starting line number
                - end_line: Ending line number
                - path: File path
                - error: Error message if failed
        """
        try:
            full_path = self._validate_path(file_path)
            
            if not full_path.exists():
                return self._error_response(f"File not found: {file_path}")
            
            if not full_path.is_file():
                return self._error_response(f"Path is not a file: {file_path}")
            
            if start_line < 1:
                return self._error_response("start_line must be >= 1")
            
            if end_line < start_line:
                return self._error_response("end_line must be >= start_line")
            
            # Read file lines
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
            except UnicodeDecodeError:
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    all_lines = f.readlines()
            
            # Validate line numbers
            total_lines = len(all_lines)
            if start_line > total_lines:
                return self._error_response(
                    f"start_line {start_line} exceeds file length {total_lines}"
                )
            
            # Adjust end_line if it exceeds file length
            actual_end = min(end_line, total_lines)
            
            # Extract lines (convert to 0-indexed)
            lines = [line.rstrip('\n\r') for line in all_lines[start_line - 1:actual_end]]
            
            rel_path = str(full_path.relative_to(self.project_path))
            
            return self._success_response(
                lines=lines,
                start_line=start_line,
                end_line=actual_end,
                path=rel_path
            )
        
        except ProjectFolderError as e:
            return self._error_response(str(e))
        except PermissionError:
            return self._error_response(f"Permission denied: {file_path}")
        except Exception as e:
            return self._error_response(f"Failed to get line range: {str(e)}")
    
    def search_files(
        self, 
        pattern: str, 
        is_regex: bool = False, 
        case_sensitive: bool = True,
        file_pattern: str = "*"
    ) -> Dict[str, Any]:
        """
        Search for a string or regex pattern across all files.
        
        Args:
            pattern: String or regex pattern to search for
            is_regex: If True, treat pattern as regex
            case_sensitive: If True, search is case-sensitive
            file_pattern: Glob pattern for filtering which files to search
            
        Returns:
            Dictionary with:
                - success: True if operation succeeded
                - matches: List of match dictionaries with:
                    - file: Relative file path
                    - line_number: Line number (1-indexed)
                    - line: Content of the matching line
                - count: Total number of matches
                - error: Error message if failed
        """
        try:
            matches = []
            
            # Compile regex if needed
            if is_regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    regex = re.compile(pattern, flags)
                except re.error as e:
                    return self._error_response(f"Invalid regex pattern: {str(e)}")
            
            # Search through files
            for file_path in self.project_path.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, start=1):
                            line_content = line.rstrip('\n\r')
                            
                            # Check for match
                            found = False
                            if is_regex:
                                found = regex.search(line_content) is not None
                            else:
                                if case_sensitive:
                                    found = pattern in line_content
                                else:
                                    found = pattern.lower() in line_content.lower()
                            
                            if found:
                                rel_path = str(file_path.relative_to(self.project_path))
                                matches.append({
                                    'file': rel_path,
                                    'line_number': line_num,
                                    'line': line_content
                                })
                
                except (PermissionError, OSError):
                    # Skip files we can't read
                    continue
            
            return self._success_response(matches=matches, count=len(matches))
        
        except Exception as e:
            return self._error_response(f"Search failed: {str(e)}")
    
    def find_python_definition(
        self, 
        name: str, 
        def_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find Python class or method/function definitions by name.
        
        Args:
            name: Name of the class, method, or function to find
            def_type: Type of definition to find ('class', 'def', or None for both)
            
        Returns:
            Dictionary with:
                - success: True if operation succeeded
                - definitions: List of definition dictionaries with:
                    - type: 'class' or 'function' or 'method'
                    - name: Name of the definition
                    - file: Relative file path
                    - start_line: Starting line number (1-indexed)
                    - end_line: Ending line number (1-indexed)
                    - text: Full text of the definition
                - count: Total number of definitions found
                - error: Error message if failed
        """
        try:
            definitions = []
            
            # Build regex pattern based on def_type
            if def_type == 'class':
                pattern = rf'^\s*class\s+{re.escape(name)}\s*[\(:]'
            elif def_type == 'def':
                pattern = rf'^\s*def\s+{re.escape(name)}\s*\('
            else:
                # Match both class and def
                pattern = rf'^\s*(class|def)\s+{re.escape(name)}\s*[\(:]'
            
            regex = re.compile(pattern)
            
            # Search through Python files
            for file_path in self.project_path.rglob("*.py"):
                if not file_path.is_file():
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Search for definitions
                    for i, line in enumerate(lines):
                        match = regex.match(line)
                        if match:
                            # Determine indentation and type
                            indent = self._get_indentation(line)
                            
                            # Determine if it's a class, method, or function
                            if 'class' in line:
                                def_kind = 'class'
                            elif indent > 0:
                                def_kind = 'method'
                            else:
                                def_kind = 'function'
                            
                            # Find the end of the definition
                            end_idx = self._find_def_end(lines, i, indent)
                            
                            # Extract the text
                            def_lines = lines[i:end_idx + 1]
                            def_text = ''.join(def_lines)
                            
                            rel_path = str(file_path.relative_to(self.project_path))
                            
                            definitions.append({
                                'type': def_kind,
                                'name': name,
                                'file': rel_path,
                                'start_line': i + 1,  # Convert to 1-indexed
                                'end_line': end_idx + 1,  # Convert to 1-indexed
                                'text': def_text
                            })
                
                except (PermissionError, UnicodeDecodeError, OSError):
                    # Skip files we can't read
                    continue
            
            return self._success_response(definitions=definitions, count=len(definitions))
        
        except Exception as e:
            return self._error_response(f"Find definition failed: {str(e)}")


# Convenience functions for standalone use
def create_project_folder(project_path: str) -> ProjectFolder:
    """
    Create a ProjectFolder instance.
    
    Args:
        project_path: Path to the project folder
        
    Returns:
        ProjectFolder instance
    """
    return ProjectFolder(project_path)


if __name__ == '__main__':
    """
    Example usage and basic smoke tests.
    """
    import json
    import tempfile
    import shutil
    
    print("=== MCP Utils Example Usage ===\n")
    
    # Create a temporary test project
    test_dir = tempfile.mkdtemp(prefix="mcp_test_")
    print(f"Created test directory: {test_dir}\n")
    
    try:
        # Initialize ProjectFolder
        pf = ProjectFolder(test_dir)
        print(f"Initialized ProjectFolder: {pf.project_path}\n")
        
        # Test 1: Create files
        print("1. Creating test files...")
        result = pf.create_file("test.py", """def hello(name):
    \"\"\"Say hello to someone.\"\"\"
    print(f"Hello, {name}!")
    return True

class Greeter:
    def __init__(self, greeting):
        self.greeting = greeting
    
    def greet(self, name):
        print(f"{self.greeting}, {name}!")
""")
        print(f"   Created test.py: {result['success']}")
        
        result = pf.create_file("subdir/data.txt", "Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        print(f"   Created subdir/data.txt: {result['success']}\n")
        
        # Test 2: List files
        print("2. Listing files...")
        result = pf.list_files()
        print(f"   Found {result['count']} files:")
        for file in result['files']:
            print(f"   - {file['path']} ({file['size_bytes']} bytes, {file['size_lines']} lines)")
        print()
        
        # Test 3: Load file
        print("3. Loading test.py...")
        result = pf.load_file("test.py")
        if result['success']:
            print(f"   Loaded {result['metadata']['size_lines']} lines")
            print(f"   First 50 chars: {result['content'][:50]}...")
        print()
        
        # Test 4: Get line range
        print("4. Getting lines 5-7 from test.py...")
        result = pf.get_line_range("test.py", 5, 7)
        if result['success']:
            print(f"   Lines {result['start_line']}-{result['end_line']}:")
            for line in result['lines']:
                print(f"      {line}")
        print()
        
        # Test 5: Search files
        print("5. Searching for 'print' in all files...")
        result = pf.search_files("print", file_pattern="*.py")
        if result['success']:
            print(f"   Found {result['count']} matches:")
            for match in result['matches']:
                print(f"   - {match['file']}:{match['line_number']}: {match['line'][:60]}")
        print()
        
        # Test 6: Find Python definitions
        print("6. Finding 'hello' function...")
        result = pf.find_python_definition("hello", def_type="def")
        if result['success'] and result['count'] > 0:
            defn = result['definitions'][0]
            print(f"   Found {defn['type']} in {defn['file']} at lines {defn['start_line']}-{defn['end_line']}")
            print(f"   Text preview: {defn['text'][:80]}...")
        print()
        
        print("7. Finding 'Greeter' class...")
        result = pf.find_python_definition("Greeter", def_type="class")
        if result['success'] and result['count'] > 0:
            defn = result['definitions'][0]
            print(f"   Found {defn['type']} in {defn['file']} at lines {defn['start_line']}-{defn['end_line']}")
        print()
        
        # Test 7: Remove file
        print("8. Removing subdir/data.txt...")
        result = pf.remove_file("subdir/data.txt")
        print(f"   Removed: {result['success']}")
        
        # Test path validation
        print("\n9. Testing security (path validation)...")
        result = pf.load_file("../outside.txt")
        if not result['success'] and 'outside the project folder' in result.get('error', ''):
            print(f"   ✓ Correctly rejected path traversal attempt")
        
        print("\n=== All tests completed successfully! ===")
    
    finally:
        # Clean up
        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")
