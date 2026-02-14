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
import logging
import json
import subprocess
import datetime
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from fastmcp.exceptions import ToolError
from checklist import ChecklistFactory
from patch import pattern_replace, multiline_replace, fuzzy_multiline_replace

# Set up logger for this module
logger = logging.getLogger(__name__)


class ProjectFolderError(ToolError):
    """Custom exception for project folder operations. Inherits from ToolError for MCP integration."""
    pass


class ProjectFolder:
    """
    Manages file operations within a specified project folder.
    
    All file paths are validated to ensure they remain within the project
    folder, preventing path traversal attacks.
    
    Attributes:
        project_path: Absolute path to the project folder
        exclude_patterns: List of patterns to exclude from file operations
        _metadata_cache: Cache for file metadata with modification times

    Project folder structure:
        /base_path/
            /current/  - current working directory
                /code/ - current code folder
                /checklists/ - checklists folder
            /history/ - history of previous code versions
                /1/
                /2/
                ...
    """
    
    DEFAULT_EXCLUDE_PATTERNS = ['.venv', '__pycache__', '**/*.pyc', '.ruff_cache']

    def __init__(self, base_path: str, exclude_patterns: Optional[List[str]] = None):
        """
        Initialize ProjectFolder with a project directory.
        
        Args:
            project_path: Path to the project folder (relative or absolute)
            exclude_patterns: List of glob patterns to exclude from file operations
                            (default: ['.venv/**/*', '__pycache__/**', '**/*.pyc'] to exclude 
                            virtual environments, cache, and compiled files)
            
        Raises:
            ProjectFolderError: If the project path doesn't exist or isn't a directory
        """
        self.base_path = Path(base_path).resolve()
        
        if not self.base_path.exists():
            raise ProjectFolderError(f"Project base path does not exist: {base_path}")
        
        if not self.base_path.is_dir():
            raise ProjectFolderError(f"Project base path is not a directory: {base_path}")

        # Set standard subdirectories
        self.code_path = self.base_path / "current" / "code"
        self.checklists_path = self.base_path / "current" / "checklists"
        self.history_path = self.base_path / "history"
        # Create standard subdirectories
        self.code_path.mkdir(parents=True, exist_ok=True)
        self.checklists_path.mkdir(parents=True, exist_ok=True)
        self.history_path.mkdir(parents=True, exist_ok=True)
        
        self.exclude_patterns = exclude_patterns if exclude_patterns is not None else self.DEFAULT_EXCLUDE_PATTERNS
        self._metadata_cache = {}

        # Checklist parameters
        self.current_iteration = 1
        self.current_role = "agent"
        self.checklist_factory = ChecklistFactory(self.checklists_path)
    
    def _validate_code_path(self, file_path: Union[str, Path]) -> Path:
        """
        Validate that a file path is within the project folder.
        
        Args:
            file_path: Relative path (relative to project folder). Absolute paths are not allowed.
            
        Returns:
            Absolute Path object within the project folder
            
        Raises:
            ProjectFolderError: If path is absolute or outside the project folder
        """
        # Convert to Path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        # Reject absolute paths
        if file_path.is_absolute():
            raise ProjectFolderError(
                f"Absolute paths are not allowed. Use relative paths only: {file_path}"
            )
        
        # Make it relative to project folder and resolve
        full_path = (self.code_path / file_path).resolve()
        
        # Check if the path is within project folder
        try:
            full_path.relative_to(self.code_path)
        except ValueError:
            raise ProjectFolderError(
                f"Path '{file_path}' is outside the project folder"
            )
        
        return full_path
    
    def _is_excluded(self, file_path: Path) -> bool:
        """
        Check if a file path should be excluded based on exclude patterns.
        
        Args:
            file_path: Absolute path to check
            
        Returns:
            True if the path should be excluded, False otherwise
        """
        try:
            rel_path = file_path.relative_to(self.code_path)
            rel_path_str = str(rel_path)
            
            for pattern in self.exclude_patterns:
                # Use glob-style matching for the path itself
                if rel_path.match(pattern):
                    return True
                
                # For directory patterns (without wildcards), check if path is inside that directory
                # This handles patterns like '.venv' or '__pycache__' to exclude everything inside them
                if '**' not in pattern and '*' not in pattern:
                    # Check if this path is the excluded directory itself
                    if rel_path_str == pattern:
                        return True
                    # Check if this path is inside the excluded directory
                    if rel_path_str.startswith(pattern + '/'):
                        return True
        except ValueError:
            # Path is not relative to base_path
            pass
        
        return False
    
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
        Find the end line of a Python definition block using indentation. Includes any code and comments 
        that follow the indentation level of the definition.
        
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
            
            # Check if it's empty or comment
            stripped = line.strip()
            if not stripped:
                continue

            # Check indentation
            indent = self._get_indentation(line)

            if stripped.startswith('#'):
                # Only update end_idx for comment lines if they follow the indentation level of code lines
                if indent > start_indent:
                    end_idx = i
            else:
                # If indentation is less than or equal to start, we've exited the block
                if indent <= start_indent:
                    break
                # This is a code line with proper indentation
                end_idx = i
        
        return end_idx
    
    def get_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get metadata for a file.
        
        Args:
            file_path: Absolute path to the file
            
        Returns:
            Dictionary with file metadata
        """
        # Convert to Path and resolve to absolute path
        if isinstance(file_path, str):
            file_path = Path(file_path)

        try:
            stat_info = os.stat(file_path)
            rel_path = str(file_path.relative_to(self.code_path))
            mtime = stat_info.st_mtime

            if rel_path in self._metadata_cache:
                cached = self._metadata_cache[rel_path]
                if cached['mtime'] == mtime:
                    return cached

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)

            metadata = {
                'path': rel_path,
                'mtime': mtime,
                'size_bytes': stat_info.st_size,
                'size_lines': line_count
            }
            self._metadata_cache[rel_path] = metadata
            return metadata
        except Exception as e:
            return {
                'path': str(file_path.relative_to(self.code_path)),
                'error': str(e)
            }
    
    def _clear_metadata_cache(self, file_path: Path):
        """
        Clear metadata cache for a specific file.
        
        Args:
            file_path: Absolute path to the file
        """
        try:
            rel_path = str(file_path.relative_to(self.code_path))
            if rel_path in self._metadata_cache:
                del self._metadata_cache[rel_path]
        except Exception: # File not in project folder or other error
            pass

    def list_files(self, pattern: str = "*") -> List[Dict[str, Any]]:
        """
        List all files in the project folder recursively.
        
        Args:
            pattern: Glob pattern for filtering files (default: "*" for all files)
            
        Returns:
            List of file metadata dictionaries
            
        Raises:
            ProjectFolderError: If operation fails
        """
        try:
            files = []
            
            # Use rglob for recursive search
            for file_path in self.code_path.rglob(pattern):
                if file_path.is_file() and not self._is_excluded(file_path):
                    files.append(self.get_metadata(file_path))
            
            # Sort by path for consistent output
            files.sort(key=lambda x: x['path'])
            
            return files
        
        except Exception as e:
            raise ProjectFolderError(f"Failed to list files: {str(e)}")
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and return the complete contents of a file.
        
        Args:
            file_path: Relative path to the file (relative to project base folder)
            
        Returns:
            Dictionary with:
                - content: File contents as list of lines (line endings removed)
                - metadata: File metadata
                
        Raises:
            ProjectFolderError: If file not found, not a text file, or operation fails
        """
        try:
            full_path = self._validate_code_path(file_path)
            
            if not full_path.exists():
                raise ProjectFolderError(f"File not found: {file_path}")
            
            if not full_path.is_file():
                raise ProjectFolderError(f"Path is not a file: {file_path}")
            
            # Try to read as text
            with open(full_path, 'r', encoding='utf-8') as f:
                content = [line.rstrip('\n\r') for line in f]
            
            metadata = self.get_metadata(full_path)
            
            logger.info(f"load_file({file_path}): {len(content)} lines")
            
            return {'content': content, 'metadata': metadata}
        except UnicodeDecodeError:
            raise ProjectFolderError(f"File is not a text file: {file_path}")
        except ProjectFolderError:
            raise
        except PermissionError:
            raise ProjectFolderError(f"Permission denied: {file_path}")
        except Exception as e:
            raise ProjectFolderError(f"Failed to load file: {str(e)}")
    
    def create_file(self, file_path: str, content: Union[str, List[str]], overwrite: bool = False) -> Dict[str, Any]:
        """
        Create a new file with the given content.
        
        Args:
            file_path: Relative path to the file (relative to project folder)
            content: Content to write to the file (string or list of lines)
            overwrite: If True, overwrite existing file. If False, fail if file exists. Default: False
            
        Returns:
            Dictionary with:
                - status: 'success', 'error', or 'no_change'
                - message: Description of the result
                - metadata: File metadata (only present on success or no_change)
                - error: Error details (only present on error)
        """
        try:
            full_path = self._validate_code_path(file_path)
            
            # Track old content if file exists
            old_line_count = None
            old_content = None
            if full_path.exists():
                if not overwrite:
                    return {
                        'status': 'error',
                        'message': f"File already exists: {file_path}. Use overwrite=True to replace it.",
                        'error': 'file_exists'
                    }
                # Get old content for logging
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        old_content = f.read()
                        old_line_count = old_content.count('\n') + (1 if old_content and not old_content.endswith('\n') else 0)
                except:
                    pass
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert list to string if needed
            if isinstance(content, list):
                content = '\n'.join(content)
            
            # Check if content is unchanged (for overwrite case)
            if old_content is not None and old_content == content:
                metadata = self.get_metadata(full_path)
                logger.info(f"create_file({file_path}, overwrite, no_change): content unchanged")
                return {
                    'status': 'no_change',
                    'message': f"File content unchanged: {file_path}",
                    'metadata': metadata
                }
            
            # Write the file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Clear cache for this file
            self._clear_metadata_cache(full_path)
            
            # Log the operation
            new_line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            if old_line_count is not None:
                diff = new_line_count - old_line_count
                sign = '+' if diff >= 0 else ''
                logger.info(f"create_file({file_path}, overwrite, changed): {old_line_count} -> {new_line_count} ({sign}{diff}) lines")
            else:
                logger.info(f"create_file({file_path}): {new_line_count} lines")
            
            metadata = self.get_metadata(full_path)
            return {
                'status': 'success',
                'message': f"File {'updated' if old_line_count is not None else 'created'}: {file_path}",
                'metadata': metadata
            }
        
        except ProjectFolderError as e:
            return {
                'status': 'error',
                'message': str(e),
                'error': 'validation_error'
            }
        except PermissionError:
            return {
                'status': 'error',
                'message': f"Permission denied: {file_path}",
                'error': 'permission_denied'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Failed to create file: {str(e)}",
                'error': 'unknown_error'
            }
    
    def remove_file(self, file_path: str) -> str:
        """
        Remove a file from the project folder.
        
        Args:
            file_path: Relative path to the file (relative to project folder)
            
        Returns:
            Relative path of the removed file
            
        Raises:
            ProjectFolderError: If file not found, path is not a file, or operation fails
        """
        try:
            full_path = self._validate_code_path(file_path)
            
            if not full_path.exists():
                raise ProjectFolderError(f"File not found: {file_path}")
            
            if not full_path.is_file():
                raise ProjectFolderError(f"Path is not a file: {file_path}")
            
            # Get relative path before deletion
            rel_path = str(full_path.relative_to(self.code_path))
            
            # Remove from cache
            self._clear_metadata_cache(full_path)

            # Delete the file
            full_path.unlink()
            
            return rel_path
        
        except ProjectFolderError:
            raise
        except PermissionError:
            raise ProjectFolderError(f"Permission denied: {file_path}")
        except Exception as e:
            raise ProjectFolderError(f"Failed to remove file: {str(e)}")
    
    def get_line_range(self, file_path: str, start_line: int, end_line: int) -> Dict[str, Any]:
        """
        Retrieve a specific range of lines from a file.
        
        Args:
            file_path: Relative path to the file (relative to project folder)
            start_line: Starting line number (1-indexed, inclusive)
            end_line: Ending line number (1-indexed, inclusive)
            
        Returns:
            Dictionary with:
                - lines: List of lines in the range
                - start_line: Starting line number
                - end_line: Ending line number (adjusted if needed)
                - path: Relative file path
                
        Raises:
            ProjectFolderError: If file not found, invalid line numbers, or operation fails
        """
        try:
            full_path = self._validate_code_path(file_path)
            
            if not full_path.exists():
                raise ProjectFolderError(f"File not found: {file_path}")
            
            if not full_path.is_file():
                raise ProjectFolderError(f"Path is not a file: {file_path}")
            
            if start_line < 1:
                raise ProjectFolderError("start_line must be >= 1")
            
            if end_line < start_line:
                raise ProjectFolderError("end_line must be >= start_line")
            
            # Read file lines
            with open(full_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Validate line numbers
            total_lines = len(all_lines)
            if start_line > total_lines:
                raise ProjectFolderError(f"start_line {start_line} exceeds file length {total_lines}")
            
            # Adjust end_line if it exceeds file length
            actual_end = min(end_line, total_lines)
            
            # Extract lines (convert to 0-indexed)
            lines = [line.rstrip('\n\r') for line in all_lines[start_line - 1:actual_end]]
            
            rel_path = str(full_path.relative_to(self.code_path))
            
            return {
                'lines': lines,
                'start_line': start_line,
                'end_line': actual_end,
                'path': rel_path
            }
        except UnicodeDecodeError:
            raise ProjectFolderError(f"File is not a text file: {file_path}")
        except ProjectFolderError:
            raise
        except PermissionError:
            raise ProjectFolderError(f"Permission denied: {file_path}")
        except Exception as e:
            raise ProjectFolderError(f"Failed to get line range: {str(e)}")
    
    def search_files(
        self, 
        pattern: str, 
        is_regex: bool = False, 
        case_sensitive: bool = True,
        file_pattern: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Search for a string or regex pattern across all files.
        
        Args:
            pattern: String or regex pattern to search for
            is_regex: If True, treat pattern as regex
            case_sensitive: If True, search is case-sensitive
            file_pattern: Glob pattern for filtering which files to search
            
        Returns:
            List of match dictionaries with:
                - file: Relative file path
                - line_number: Line number (1-indexed)
                - line: Content of the matching line
                
        Raises:
            ProjectFolderError: If regex is invalid or search fails
        """
        try:
            matches = []
            
            # Compile regex if needed
            if is_regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    regex = re.compile(pattern, flags)
                except re.error as e:
                    raise ProjectFolderError(f"Invalid regex pattern: {str(e)}")
            
            # Search through files
            for file_path in self.code_path.rglob(file_pattern):
                if not file_path.is_file() or self._is_excluded(file_path):
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
                                rel_path = str(file_path.relative_to(self.code_path))
                                matches.append({
                                    'file': rel_path,
                                    'line_number': line_num,
                                    'line': line_content
                                })
                
                except (PermissionError, OSError, UnicodeDecodeError):
                    # Skip files we can't read or decode
                    continue
            
            return matches
        
        except ProjectFolderError:
            raise
        except Exception as e:
            raise ProjectFolderError(f"Search failed: {str(e)}")
    
    def replace_in_files(
        self,
        pattern: str,
        replacement: str,
        is_regex: bool = False,
        file_pattern: str = "*"
    ) -> Dict[str, int]:
        """
        Search and replace a pattern across all matching files.
        
        For each file that matches the file_pattern, loads the file,
        performs pattern replacement, and saves it if any replacements were made.
        
        Args:
            pattern: String or regex pattern to search for
            replacement: String to replace matches with
            is_regex: If True, treat pattern as regex
            file_pattern: Glob pattern for filtering which files to process
            
        Returns:
            Dictionary mapping relative file path to number of replacements made
            
        Raises:
            ProjectFolderError: If regex is invalid or operation fails
        """
        try:
            results = {}
            
            # Validate regex pattern if needed
            if is_regex:
                try:
                    re.compile(pattern)
                except re.error as e:
                    raise ProjectFolderError(f"Invalid regex pattern: {str(e)}")
            
            # Process each matching file
            for file_path in self.code_path.rglob(file_pattern):
                if not file_path.is_file() or self._is_excluded(file_path):
                    continue
                
                try:
                    # Load file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code_lines = [line.rstrip('\n\r') for line in f]
                    
                    # Perform replacement
                    num_replacements = pattern_replace(code_lines, pattern, replacement, is_regex)
                    
                    # Save if replacements were made
                    if num_replacements > 0:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(code_lines))
                        
                        # Clear cache for this file
                        self._clear_metadata_cache(file_path)
                        
                        # Add to results
                        rel_path = str(file_path.relative_to(self.code_path))
                        results[rel_path] = num_replacements
                        
                        logger.info(f"replace_in_files({rel_path}): {num_replacements} replacement(s)")
                
                except (PermissionError, OSError, UnicodeDecodeError):
                    # Skip files we can't read, decode, or write
                    continue
            
            return results
        
        except ProjectFolderError:
            raise
        except Exception as e:
            raise ProjectFolderError(f"Replace in files failed: {str(e)}")

    def multiline_replace_in_file(
        self,
        file_path: str,
        search_lines: List[str],
        replace_lines: List[str],
        only_around_line: Optional[int] = None
    ) -> int:
        """
        Search and replace a multiline pattern in a specific file.
        
        Loads the file, performs multiline replacement, and saves it if any
        replacements were made.
        
        Args:
            file_path: Relative path to the file (relative to project folder)
            search_lines: List of lines to search for (must match exactly)
            replace_lines: List of lines to replace with
            only_around_line: If not None, only replace the match closest to this line number (1-indexed)
            
        Returns:
            Number of replacement operations performed
            
        Raises:
            ProjectFolderError: If file not found or operation fails
        """
        try:
            full_path = self._validate_code_path(file_path)
            
            if not full_path.exists():
                raise ProjectFolderError(f"File not found: {file_path}")
            
            if not full_path.is_file():
                raise ProjectFolderError(f"Path is not a file: {file_path}")
            
            # Check if file should be excluded
            if self._is_excluded(full_path):
                raise ProjectFolderError(f"File matches exclude patterns: {file_path}")
            
            # Load file
            with open(full_path, 'r', encoding='utf-8') as f:
                code_lines = [line.rstrip('\n\r') for line in f]
            
            # Convert 1-indexed to 0-indexed for only_around_line
            around_line_0based = only_around_line - 1 if only_around_line is not None else None
            
            # Perform replacement
            num_replacements = multiline_replace(code_lines, search_lines, replace_lines, around_line_0based)
            
            # Save if replacements were made
            if num_replacements > 0:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(code_lines))
                
                # Clear cache for this file
                self._clear_metadata_cache(full_path)
                
                rel_path = str(full_path.relative_to(self.code_path))
                logger.info(f"multiline_replace_in_file({rel_path}): {num_replacements} replacement(s)")
            
            return num_replacements
        
        except UnicodeDecodeError:
            raise ProjectFolderError(f"File is not a text file: {file_path}")
        except ProjectFolderError:
            raise
        except PermissionError:
            raise ProjectFolderError(f"Permission denied: {file_path}")
        except Exception as e:
            raise ProjectFolderError(f"Multiline replace failed: {str(e)}")

    def fuzzy_replace_in_file(
        self,
        file_path: str,
        search_lines: List[str],
        replace_lines: List[str],
        around_line: int
    ) -> Tuple[str, Optional[int]]:
        """
        Search and replace a multiline pattern in a specific file using fuzzy matching.
        
        This method finds the closest approximate match to the search pattern near the
        specified line and replaces it. Allows for small differences (typos, spacing)
        between the search pattern and actual code.
        
        Args:
            file_path: Relative path to the file (relative to project folder)
            search_lines: List of lines to search for (approximate match allowed)
            replace_lines: List of lines to replace with
            around_line: Line number around which to search (1-indexed, required)
            
        Returns:
            Actual line number (1-indexed) where replacement was made, or None if no match found
            
        Raises:
            ProjectFolderError: If file not found or operation fails
        """
        try:
            full_path = self._validate_code_path(file_path)
            
            if not full_path.exists():
                raise ProjectFolderError(f"File not found: {file_path}")
            
            if not full_path.is_file():
                raise ProjectFolderError(f"Path is not a file: {file_path}")
            
            # Check if file should be excluded
            if self._is_excluded(full_path):
                raise ProjectFolderError(f"File matches exclude patterns: {file_path}")
            
            # Load file
            with open(full_path, 'r', encoding='utf-8') as f:
                code_lines = [line.rstrip('\n\r') for line in f]
            
            # Convert 1-indexed to 0-indexed for around_line
            around_line -= 1
            line_tolerance = 10
            start_range = range(max(0, around_line - line_tolerance), min(len(code_lines), around_line + line_tolerance + 1))

            # Perform fuzzy replacement
            matched_line = fuzzy_multiline_replace(code_lines, search_lines, replace_lines, start_range=start_range)
            
            # Save if replacement was made
            if matched_line is not None:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(code_lines))
                
                # Clear cache for this file
                self._clear_metadata_cache(full_path)
                
                rel_path = str(full_path.relative_to(self.code_path))
                logger.info(f"fuzzy_replace_in_file({rel_path}): replacement at line {matched_line + 1}")
                
                return "Replace successful", matched_line + 1
            
            # if no match was found, try to match wider and return a matching line if found
            matched_line = fuzzy_multiline_replace(code_lines, search_lines, replace_lines, start_range=range(0, len(code_lines)))
            if matched_line is not None:
                return f"Could not find close match around line {around_line + 1}, but there is a match for this search pattern at line {matched_line + 1}. Try adjusting the around_line parameter.", None
            else:
                return "No matching pattern found in the whole file. I tried to find the pattern in the whole file, and it wasn't found. ", None
            
        except UnicodeDecodeError:
            raise ProjectFolderError(f"File is not a text file: {file_path}")
        except ProjectFolderError:
            raise
        except PermissionError:
            raise ProjectFolderError(f"Permission denied: {file_path}")
        except Exception as e:
            raise ProjectFolderError(f"Fuzzy replace failed: {str(e)}")

    def run_ruff_check(
        self,
        file_pattern: str = "**/*.py",
        fix: bool = False
    ) -> Dict[str, Any]:
        """
        Run Ruff linter on project files and return structured results.
        
        Uses Ruff's JSON output format to return detailed linting information.
        Ruff must be installed and available in PATH.
        
        Args:
            file_pattern: Glob pattern for files to check (default: "**/*.py")
            fix: If True, automatically fix fixable issues (default: False)
            
        Returns:
            Dictionary with:
                - success: Boolean - False if issues found or execution failed, True only if no issues
                - error: Error message (present if success=False)
                - issues: List of issue dictionaries, if there were any. Each issue contains:
                    - file: Relative file path
                    - line: Line number (1-indexed)
                    - column: Column number (1-indexed)
                    - code: Rule code (e.g., "F401", "E501")
                    - message: Issue description
                    - fixable: Whether the issue can be auto-fixed

        Note:
            Returns success=False and error="There were syntax issues" when linting issues are found.
            Returns success=False with specific error when Ruff execution fails.
            Returns success=True when there are no issues.
        """
        try:
            # Build list of files to check
            files_to_check = []
            for file_path in self.code_path.rglob(file_pattern):
                if file_path.is_file() and not self._is_excluded(file_path):
                    files_to_check.append(str(file_path))
            
            if not files_to_check:
                return {
                    'issues': [],
                    'total_issues': 0,
                    'total_files': 0
                }
            
            # Build ruff command
            cmd = ['ruff', 'check', '--output-format', 'json']
            if fix:
                cmd.append('--fix')
            cmd.extend(files_to_check)
            
            # Run ruff
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.code_path)
            )
            
            # Ruff exits with non-zero if issues found, which is expected
            if result.returncode not in [0, 1]:
                # Check if ruff is not installed
                if result.returncode == 127 or 'not found' in result.stderr.lower():
                    error_msg = "Ruff is not installed or not in PATH"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg
                    }
                error_msg = f"Ruff execution failed: {result.stderr}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Parse JSON output
            if result.stdout:
                ruff_output = json.loads(result.stdout)
            else:
                ruff_output = []
            
            # Convert to our format with relative paths
            issues = []
            files_with_issues = set()
            
            for issue in ruff_output:
                file_path = Path(issue['filename'])
                try:
                    rel_path = str(file_path.relative_to(self.code_path))
                except ValueError:
                    rel_path = str(file_path)
                
                files_with_issues.add(rel_path)
                
                issues.append({
                    'file': rel_path,
                    'line': issue['location']['row'],
                    'column': issue['location']['column'],
                    'code': issue['code'],
                    'message': issue['message'],
                    'fixable': issue.get('fix', None) is not None
                })
            
            logger.info(f"run_ruff_check: found {len(issues)} issue(s) in {len(files_with_issues)} file(s)")
            

            
            if len(issues) > 0:
                result = {
                    'success': False,
                    'error': "There were syntax issues",
                    'issues': issues
                }                
            else:
                result = {'success': True}
            return result
        
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse Ruff output: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'issues': [],
                'total_issues': 0,
                'total_files': 0
            }
        except FileNotFoundError:
            error_msg = "Ruff is not installed or not in PATH"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'issues': [],
                'total_issues': 0,
                'total_files': 0
            }
        except Exception as e:
            error_msg = f"Ruff check failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'issues': [],
                'total_issues': 0,
                'total_files': 0
            }


    def find_python_definition(
        self, 
        name: str, 
        def_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find Python class or method/function definitions by name.
        
        Args:
            name: Name of the class, method, or function to find
            def_type: Type of definition to find ('class', 'def', or None for both)
            
        Returns:
            List of definition dictionaries with:
                - name: Name of the definition
                - file: Relative file path
                - start_line: Starting line number (1-indexed)
                - end_line: Ending line number (1-indexed)
                - text: Full text of the definition
                
        Raises:
            ProjectFolderError: If operation fails
        """
        try:
            definitions = []
            
            # Build regex pattern based on def_type
            if def_type == 'class':
                pattern = rf'^\s*class\s+{re.escape(name)}\s*[\(:]'
            elif def_type == 'def':
                pattern = rf'^\s*def\s+{re.escape(name)}\s*\('
            elif def_type == 'method':
                pattern = rf'^\s*def\s+{re.escape(name)}\s*\((self|cls)[,\)]'
            else:
                # Match both class and def
                pattern = rf'^\s*(class|def)\s+{re.escape(name)}\s*[\(:]'
            
            regex = re.compile(pattern)
            
            # Search through Python files
            for file_path in self.code_path.rglob("*.py"):
                if not file_path.is_file() or self._is_excluded(file_path):
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
                            
                            # Find the end of the definition
                            end_idx = self._find_def_end(lines, i, indent)
                            
                            # Extract the text
                            def_lines = lines[i:end_idx + 1]
                            def_text = ''.join(def_lines)
                            
                            rel_path = str(file_path.relative_to(self.code_path))
                            
                            definitions.append({
                                'name': name,
                                'file': rel_path,
                                'start_line': i + 1,  # Convert to 1-indexed
                                'end_line': end_idx + 1,  # Convert to 1-indexed
                                'text': def_text
                            })
                
                except (PermissionError, UnicodeDecodeError, OSError):
                    # Skip files we can't read
                    continue
            
            return definitions
        
        except Exception as e:
            raise ProjectFolderError(f"Find definition failed: {str(e)}")

    def _next_snapshot_id(self) -> int:
        """ Determine the next snapshot ID based on existing snapshots. """
        existing_ids = []
        if self.history_path.exists():
            for entry in self.history_path.iterdir():
                if entry.is_dir() and entry.name.isdigit():
                    existing_ids.append(int(entry.name))
        return max(existing_ids, default=0) + 1

    def create_snapshot(self, label=None) -> str:
        """ 
            Create a snapshot of the current project folder state.
            A folder in history/ is created with the name equals snapshot ID.
            Snapshot ID is a snapshot number (1,2,3 etc) and it returned
            current/code contents is copied into history/<ID>/code, excluding DEFAULT_EXCLUDE_PATTERN
            current/checklists contents is copied into history/<ID>/checklists
            history/<ID>/metadata.json is created with:
                - timestamp: ISO formatted timestamp of snapshot creation
                - label: Snapshot label
            If snapshot label is not provided, a default label with timestamp is used.
        """
        snapshot_id = str(self._next_snapshot_id())
        snapshot_path = self.history_path / snapshot_id
        code_snapshot_path = snapshot_path / "code"
        checklists_snapshot_path = snapshot_path / "checklists"
        metadata_path = snapshot_path / "metadata.json"

        # Create snapshot directories
        code_snapshot_path.mkdir(parents=True, exist_ok=True)
        checklists_snapshot_path.mkdir(parents=True, exist_ok=True)

        # Copy code folder excluding DEFAULT_EXCLUDE_PATTERN
        if self.code_path.exists():
            for item in self.code_path.rglob('*'):
                if self._is_excluded(item):
                    continue
                relative_item_path = item.relative_to(self.code_path)
                dest_item_path = code_snapshot_path / relative_item_path
                if item.is_dir():
                    dest_item_path.mkdir(parents=True, exist_ok=True)
                else:
                    dest_item_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_item_path)

        # Copy checklists folder
        if self.checklists_path.exists():
            shutil.copytree(self.checklists_path, checklists_snapshot_path, dirs_exist_ok=True)

        # Create metadata.json
        timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
        if label is None:
            label = f"Snapshot at {timestamp}"
        metadata = {
            'id': snapshot_id,
            'timestamp': timestamp,
            'label': label
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4)

        logger.info(f"Created snapshot {snapshot_id} with label: {label}")
        return snapshot_id
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """ 
            List all snapshots with their metadata.
            Returns a list of dictionaries with:
                - id: Snapshot ID
                - timestamp: Snapshot creation timestamp
                - label: Snapshot label
        """
        snapshots = []
        if self.history_path.exists():
            for entry in sorted(self.history_path.iterdir(), key=lambda e: int(e.name) if e.name.isdigit() else float('inf')):
                if entry.is_dir() and entry.name.isdigit():
                    metadata_path = entry / "metadata.json"
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                                snapshots.append(metadata)
                        except (json.JSONDecodeError, OSError):
                            continue
        return snapshots
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """ 
            Restore the project folder to the state of the specified snapshot ID.
            The current code/ folder content is deleted, except DEFAULT_EXCLUDE_PATTERN, and files from the snapshot are written over.
            The current checklists/ folder content is deleted, and files from the snapshot are written over.
            Returns True if successful, False if snapshot not found or error occurs.
        """
        snapshot_path = self.history_path / snapshot_id
        code_snapshot_path = snapshot_path / "code"
        checklists_snapshot_path = snapshot_path / "checklists"

        if not snapshot_path.exists() or not snapshot_path.is_dir():
            logger.error(f"Snapshot {snapshot_id} not found")
            return False

        try:
            # Clear current code folder except excluded patterns
            if self.code_path.exists():
                # First pass: collect items to delete (excluding items in excluded directories)
                items_to_delete = []
                for item in sorted(self.code_path.rglob('*'), reverse=True):  # reverse to handle deepest first
                    if self._is_excluded(item):
                        continue
                    items_to_delete.append(item)
                
                # Second pass: delete files and empty directories
                for item in items_to_delete:
                    try:
                        if item.exists() and item.is_file():
                            item.unlink()
                        elif item.exists() and item.is_dir() and not any(item.iterdir()):
                            item.rmdir()
                    except (OSError, PermissionError):
                        pass

            # Copy code snapshot
            if code_snapshot_path.exists():
                for item in code_snapshot_path.rglob('*'):
                    relative_item_path = item.relative_to(code_snapshot_path)
                    dest_item_path = self.code_path / relative_item_path
                    if item.is_dir():
                        dest_item_path.mkdir(parents=True, exist_ok=True)
                    else:
                        dest_item_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_item_path)

            # Clear current checklists folder
            if self.checklists_path.exists():
                shutil.rmtree(self.checklists_path, ignore_errors=True)

            # Copy checklists snapshot
            if checklists_snapshot_path.exists():
                shutil.copytree(checklists_snapshot_path, self.checklists_path, dirs_exist_ok=True)

            logger.info(f"Restored snapshot {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore snapshot {snapshot_id}: {str(e)}")
            return False

    # Operations with checklists
    
    # List available checklists
    def list_checklists(self) -> List[str]:
        return self.checklist_factory.list_checklists()

    # Read checklist items, with optional filtering by completion status
    def read_checklist_items(self, checklist_name: str, completed: bool = None) -> Dict[str, Any]:
        return {"items": self.checklist_factory.get_checklist(checklist_name).get_items(completed=completed),
                "current_role": self.current_role,
                "current_iteration": self.current_iteration
        }
    
    # Add a checklist item with metadata about the creator and creation iteration
    def add_checklist_item(self, checklist_name: str, id: str, title: str, description: Union[str, List[str]], points: int):
        checklist = self.checklist_factory.get_checklist(checklist_name)
        create_iteration = self.current_iteration
        create_role = self.current_role
        if not checklist.add_item(id, title, description, points, create_role, create_iteration):
            raise ProjectFolderError(f"Checklist item with ID '{id}' already exists in checklist '{checklist_name}'")
        checklist.save()
    
    # Mark a checklist item as completed
    def complete_checklist_item(self, checklist_name: str, item_id: str):
        checklist = self.checklist_factory.get_checklist(checklist_name)
        if not checklist.complete_item(item_id):
            raise ProjectFolderError(f"Checklist item with ID '{item_id}' not found in checklist '{checklist_name}'")
        checklist.save()

    # Edit a checklist item with optional parameters, allowing to update title, description, points, and completion status
    def edit_checklist_item(self, checklist_name: str, item_id: str, title: str = None, description: Union[str, List[str], None] = None, points: int = None, completed: bool = None):
        checklist = self.checklist_factory.get_checklist(checklist_name)
        if not checklist.edit_item(item_id, title, description, points, completed):
            raise ProjectFolderError(f"Checklist item with ID '{item_id}' not found in checklist '{checklist_name}'")
        checklist.save()
    
    # Delete a checklist entirely
    def delete_checklist(self, checklist_name: str):
        self.checklist_factory.delete_checklist(checklist_name)

    # Service function to set the current actor name and iteration number, 
    # which will be used in checklist items metadata
    def set_iteration_info(self, current_iteration: int, current_role: str):
        self.current_iteration = current_iteration
        self.current_role = current_role
    