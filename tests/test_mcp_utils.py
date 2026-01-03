"""
Unit tests for mcp_utils.py module.

Tests all functionality of the ProjectFolder class including:
- Path validation and security
- File operations (list, load, create, remove)
- Line range extraction
- Search functionality
- Python definition finding
- Caching behavior
- Error handling
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_utils import ProjectFolder, ProjectFolderError


@pytest.fixture
def temp_project():
    """Create a temporary project directory with test files."""
    temp_dir = tempfile.mkdtemp(prefix="test_mcp_")
    
    # Create test file structure
    test_files = {
        "simple.txt": "Line 1\nLine 2\nLine 3",
        "test.py": """def function_one():
    '''A simple function.'''
    return 1
    # Trailing comment

class MyClass:
    def __init__(self):
        self.value = 0
    
    def method_one(self):
        return self.value

def function_two(x, y):
    return x + y
""",
        "subdir/nested.py": """class NestedClass:
    def nested_method(self):
        pass
""",
        "subdir/data.txt": "Hello\nWorld\nTest\nData\nFile",
        "empty.txt": "",
        "unicode.txt": "Hello 世界 🌍",
    }
    
    for rel_path, content in test_files.items():
        file_path = Path(temp_dir) / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def project_folder(temp_project):
    """Create a ProjectFolder instance for testing."""
    return ProjectFolder(temp_project)


class TestProjectFolderInit:
    """Tests for ProjectFolder initialization."""
    
    def test_init_with_valid_path(self, temp_project):
        """Test initialization with valid project path."""
        pf = ProjectFolder(temp_project)
        assert pf.project_path == Path(temp_project).resolve()
        assert isinstance(pf._metadata_cache, dict)
        assert len(pf._metadata_cache) == 0
    
    def test_init_with_relative_path(self, temp_project):
        """Test initialization with relative path."""
        # Change to parent directory
        original_cwd = os.getcwd()
        try:
            parent = Path(temp_project).parent
            os.chdir(parent)
            rel_path = Path(temp_project).name
            
            pf = ProjectFolder(rel_path)
            assert pf.project_path.is_absolute()
            assert pf.project_path == Path(temp_project).resolve()
        finally:
            os.chdir(original_cwd)
    
    def test_init_with_nonexistent_path(self):
        """Test initialization with non-existent path."""
        with pytest.raises(ProjectFolderError, match="does not exist"):
            ProjectFolder("/nonexistent/path/12345")
    
    def test_init_with_file_path(self, temp_project):
        """Test initialization with a file instead of directory."""
        file_path = Path(temp_project) / "simple.txt"
        with pytest.raises(ProjectFolderError, match="not a directory"):
            ProjectFolder(str(file_path))

class TestPathValidation:
    """Tests for path validation and security."""
    
    def test_validate_path_with_relative_path(self, project_folder):
        """Test validation of relative path within project."""
        result = project_folder._validate_path("simple.txt")
        assert result.is_absolute()
        assert result.name == "simple.txt"
    
    def test_validate_path_with_absolute_path(self, project_folder):
        """Test validation of absolute path within project."""
        abs_path = project_folder.project_path / "simple.txt"
        result = project_folder._validate_path(str(abs_path))
        assert result == abs_path
    
    def test_validate_path_with_subdirectory(self, project_folder):
        """Test validation of path in subdirectory."""
        result = project_folder._validate_path("subdir/nested.py")
        assert result.is_absolute()
        assert "subdir" in str(result)
    
    def test_validate_path_rejects_parent_traversal(self, project_folder):
        """Test that parent directory traversal is rejected."""
        with pytest.raises(ProjectFolderError, match="outside the project folder"):
            project_folder._validate_path("../outside.txt")
    
    def test_validate_path_rejects_absolute_outside(self, project_folder):
        """Test that absolute path outside project is rejected."""
        with pytest.raises(ProjectFolderError, match="outside the project folder"):
            project_folder._validate_path("/etc/passwd")
    
    def test_validate_path_rejects_complex_traversal(self, project_folder):
        """Test that complex traversal attempts are rejected."""
        with pytest.raises(ProjectFolderError, match="outside the project folder"):
            project_folder._validate_path("subdir/../../outside.txt")


class TestMetadataCaching:
    """Tests for metadata caching functionality."""
    
    def test_metadata_basic(self, project_folder):
        """Test basic line counting."""
        file_path = project_folder.project_path / "simple.txt"
        metadata = project_folder._file_metadata(file_path)
        assert metadata['size_lines'] == 3
    
    def test_metadata_empty_file(self, project_folder):
        """Test line counting for empty file."""
        file_path = project_folder.project_path / "empty.txt"
        metadata = project_folder._file_metadata(file_path)
        assert metadata['size_lines'] == 0
    
    def test_metadata_uses_cache(self, project_folder):
        """Test that metadata is cached."""
        file_path = project_folder.project_path / "simple.txt"
        
        # First call - should cache
        metadata1 = project_folder._file_metadata(file_path)
        assert str("simple.txt") in project_folder._metadata_cache
        
        # Second call - should use cache
        metadata2 = project_folder._file_metadata(file_path)
        assert metadata1 == metadata2
    
    def test_metadata_invalidates_on_modification(self, project_folder):
        """Test that cache is invalidated when file is modified."""
        file_path = project_folder.project_path / "simple.txt"
        
        # Get initial count
        metadata1 = project_folder._file_metadata(file_path)
        assert metadata1['size_lines'] == 3
        
        # Modify file
        import time
        time.sleep(0.01)  # Ensure mtime changes
        with open(file_path, 'a') as f:
            f.write("\nLine 4")
        
        # Should detect change and recount
        metadata2 = project_folder._file_metadata(file_path)
        assert metadata2['size_lines'] == 4
    
    def test_file_metadata_nonexistent_file(self, project_folder):
        """Test metadata for non-existent file returns error."""
        file_path = project_folder.project_path / "nonexistent.txt"
        metadata = project_folder._file_metadata(file_path)
        assert metadata['error'] is not None

class TestListFiles:
    """Tests for list_files() functionality."""
    
    def test_list_files_basic(self, project_folder):
        """Test basic file listing."""
        result = project_folder.list_files()
        
        assert result['success'] is True
        assert 'files' in result
        assert 'count' in result
        assert result['count'] > 0
        
        # Check that files are present
        file_paths = [f['path'] for f in result['files']]
        assert 'simple.txt' in file_paths
        assert 'test.py' in file_paths
    
    def test_list_files_includes_metadata(self, project_folder):
        """Test that file metadata is included."""
        result = project_folder.list_files()
        
        for file_info in result['files']:
            assert 'path' in file_info
            assert 'size_bytes' in file_info
            assert 'size_lines' in file_info
            assert file_info['size_bytes'] >= 0
            assert file_info['size_lines'] >= 0
    
    def test_list_files_with_pattern(self, project_folder):
        """Test file listing with glob pattern."""
        result = project_folder.list_files(pattern="*.py")
        
        assert result['success'] is True
        file_paths = [f['path'] for f in result['files']]
        
        # Should include Python files
        assert any('test.py' in p for p in file_paths)
        assert any('nested.py' in p for p in file_paths)
        
        # Should not include text files
        assert not any('.txt' in p for p in file_paths)
    
    def test_list_files_sorted(self, project_folder):
        """Test that files are sorted by path."""
        result = project_folder.list_files()
        
        paths = [f['path'] for f in result['files']]
        assert paths == sorted(paths)
    
    def test_list_files_empty_directory(self):
        """Test listing files in empty directory."""
        temp_dir = tempfile.mkdtemp()
        try:
            pf = ProjectFolder(temp_dir)
            result = pf.list_files()
            
            assert result['success'] is True
            assert result['count'] == 0
            assert result['files'] == []
        finally:
            shutil.rmtree(temp_dir)


class TestLoadFile:
    """Tests for load_file() functionality."""
    
    def test_load_file_basic(self, project_folder):
        """Test basic file loading."""
        result = project_folder.load_file("simple.txt")
        
        assert result['success'] is True
        assert 'content' in result
        assert result['content'] == "Line 1\nLine 2\nLine 3"
        assert 'metadata' in result
    
    def test_load_file_with_unicode(self, project_folder):
        """Test loading file with Unicode content."""
        result = project_folder.load_file("unicode.txt")
        
        assert result['success'] is True
        assert "世界" in result['content']
        assert "🌍" in result['content']
    
    def test_load_file_empty(self, project_folder):
        """Test loading empty file."""
        result = project_folder.load_file("empty.txt")
        
        assert result['success'] is True
        assert result['content'] == ""
    
    def test_load_file_with_subdirectory(self, project_folder):
        """Test loading file from subdirectory."""
        result = project_folder.load_file("subdir/data.txt")
        
        assert result['success'] is True
        assert "Hello" in result['content']
        assert "World" in result['content']
    
    def test_load_file_nonexistent(self, project_folder):
        """Test loading non-existent file."""
        result = project_folder.load_file("nonexistent.txt")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'not found' in result['error'].lower()
    
    def test_load_file_directory(self, project_folder):
        """Test attempting to load a directory."""
        result = project_folder.load_file("subdir")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'not a file' in result['error'].lower()
    
    def test_load_file_path_traversal(self, project_folder):
        """Test that path traversal is blocked."""
        result = project_folder.load_file("../outside.txt")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'outside the project folder' in result['error']


class TestCreateFile:
    """Tests for create_file() functionality."""
    
    def test_create_file_basic(self, project_folder):
        """Test basic file creation."""
        result = project_folder.create_file("new.txt", "New content")
        
        assert result['success'] is True
        assert 'metadata' in result
        
        # Verify file exists
        file_path = project_folder.project_path / "new.txt"
        assert file_path.exists()
        with open(file_path, 'r') as f:
            assert f.read() == "New content"
    
    def test_create_file_with_subdirectory(self, project_folder):
        """Test creating file with new subdirectory."""
        result = project_folder.create_file("newdir/newfile.txt", "Content")
        
        assert result['success'] is True
        
        # Verify file and directory exist
        file_path = project_folder.project_path / "newdir" / "newfile.txt"
        assert file_path.exists()
        assert file_path.parent.is_dir()
    
    def test_create_file_fails_if_exists(self, project_folder):
        """Test that creating file fails if it already exists."""
        # Try to create a file that already exists
        result = project_folder.create_file("simple.txt", "New content")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'already exists' in result['error'].lower()
        
        # Verify original content is preserved
        file_path = project_folder.project_path / "simple.txt"
        with open(file_path, 'r') as f:
            assert f.read() == "Line 1\nLine 2\nLine 3"
    
    def test_create_file_with_overwrite(self, project_folder):
        """Test that creating file with overwrite=True replaces existing."""
        result = project_folder.create_file("simple.txt", "New content", overwrite=True)
        
        assert result['success'] is True
        
        # Verify content is overwritten
        file_path = project_folder.project_path / "simple.txt"
        with open(file_path, 'r') as f:
            assert f.read() == "New content"
    
    def test_create_file_updates_cache(self, project_folder):
        """Test that creating file with overwrite updates cache with new line count."""
        file_name = "simple.txt"
        file_path = project_folder.project_path / file_name
        
        # Cache the file (original has 3 lines)
        old_metadata = project_folder._file_metadata(file_path)
        assert old_metadata['size_lines'] == 3
        assert file_name in project_folder._metadata_cache
        
        # Create/overwrite file with 4 lines
        project_folder.create_file(file_name, "New\nContent\nWith\nLines", overwrite=True)
        
        # Cache should have new count
        new_metadata = project_folder._file_metadata(file_path)
        assert new_metadata['size_lines'] == 4
    
    def test_create_file_path_traversal(self, project_folder):
        """Test that path traversal is blocked."""
        result = project_folder.create_file("../outside.txt", "Content")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'outside the project folder' in result['error']
    
    def test_create_file_with_empty_content(self, project_folder):
        """Test creating file with empty content."""
        result = project_folder.create_file("empty_new.txt", "")
        
        assert result['success'] is True
        file_path = project_folder.project_path / "empty_new.txt"
        assert file_path.exists()
        assert file_path.stat().st_size == 0


class TestRemoveFile:
    """Tests for remove_file() functionality."""
    
    def test_remove_file_basic(self, project_folder):
        """Test basic file removal."""
        result = project_folder.remove_file("simple.txt")
        
        assert result['success'] is True
        assert 'path' in result
        
        # Verify file is removed
        file_path = project_folder.project_path / "simple.txt"
        assert not file_path.exists()
    
    def test_remove_file_from_subdirectory(self, project_folder):
        """Test removing file from subdirectory."""
        result = project_folder.remove_file("subdir/data.txt")
        
        assert result['success'] is True
        
        file_path = project_folder.project_path / "subdir" / "data.txt"
        assert not file_path.exists()
    
    def test_remove_file_clears_cache(self, project_folder):
        """Test that removing file clears cache."""
        file_name = "simple.txt"
        file_path = project_folder.project_path / file_name
        
        # Cache the file
        project_folder._file_metadata(file_path)
        assert file_name in project_folder._metadata_cache
        
        # Remove file
        project_folder.remove_file(file_name)
        
        # Cache should be cleared
        assert file_name not in project_folder._metadata_cache
    
    def test_remove_file_nonexistent(self, project_folder):
        """Test removing non-existent file."""
        result = project_folder.remove_file("nonexistent.txt")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'not found' in result['error'].lower()
    
    def test_remove_file_directory(self, project_folder):
        """Test attempting to remove a directory."""
        result = project_folder.remove_file("subdir")
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_remove_file_path_traversal(self, project_folder):
        """Test that path traversal is blocked."""
        result = project_folder.remove_file("../outside.txt")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'outside the project folder' in result['error']


class TestGetLineRange:
    """Tests for get_line_range() functionality."""
    
    def test_get_line_range_basic(self, project_folder):
        """Test basic line range extraction."""
        result = project_folder.get_line_range("simple.txt", 1, 2)
        
        assert result['success'] is True
        assert 'lines' in result
        assert result['lines'] == ["Line 1", "Line 2"]
        assert result['start_line'] == 1
        assert result['end_line'] == 2
    
    def test_get_line_range_single_line(self, project_folder):
        """Test extracting single line."""
        result = project_folder.get_line_range("simple.txt", 2, 2)
        
        assert result['success'] is True
        assert result['lines'] == ["Line 2"]
    
    def test_get_line_range_all_lines(self, project_folder):
        """Test extracting all lines."""
        result = project_folder.get_line_range("simple.txt", 1, 3)
        
        assert result['success'] is True
        assert len(result['lines']) == 3
    
    def test_get_line_range_beyond_file(self, project_folder):
        """Test range that extends beyond file length."""
        result = project_folder.get_line_range("simple.txt", 2, 100)
        
        assert result['success'] is True
        assert result['end_line'] == 3  # Adjusted to file length
        assert len(result['lines']) == 2
    
    def test_get_line_range_invalid_start(self, project_folder):
        """Test invalid start line (< 1)."""
        result = project_folder.get_line_range("simple.txt", 0, 2)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'must be >= 1' in result['error']
    
    def test_get_line_range_invalid_order(self, project_folder):
        """Test end_line < start_line."""
        result = project_folder.get_line_range("simple.txt", 3, 1)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'must be >= start_line' in result['error']
    
    def test_get_line_range_start_beyond_file(self, project_folder):
        """Test start_line beyond file length."""
        result = project_folder.get_line_range("simple.txt", 100, 200)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'exceeds file length' in result['error']
    
    def test_get_line_range_empty_file(self, project_folder):
        """Test getting lines from empty file."""
        result = project_folder.get_line_range("empty.txt", 1, 1)
        
        assert result['success'] is False
        assert 'error' in result


class TestSearchFiles:
    """Tests for search_files() functionality."""
    
    def test_search_files_basic(self, project_folder):
        """Test basic string search."""
        result = project_folder.search_files("Line", file_pattern="*.txt")
        
        assert result['success'] is True
        assert 'matches' in result
        assert result['count'] > 0
        
        # Check match structure
        for match in result['matches']:
            assert 'file' in match
            assert 'line_number' in match
            assert 'line' in match
            assert 'Line' in match['line']
    
    def test_search_files_case_insensitive(self, project_folder):
        """Test case-insensitive search."""
        result = project_folder.search_files("LINE", case_sensitive=False, file_pattern="*.txt")
        
        assert result['success'] is True
        assert result['count'] > 0
    
    def test_search_files_case_sensitive(self, project_folder):
        """Test case-sensitive search."""
        result = project_folder.search_files("LINE", case_sensitive=True, file_pattern="*.txt")
        
        assert result['success'] is True
        assert result['count'] == 0  # Should not match "Line"
    
    def test_search_files_regex(self, project_folder):
        """Test regex search."""
        result = project_folder.search_files(r"Line \d+", is_regex=True, file_pattern="*.txt")
        
        assert result['success'] is True
        assert result['count'] > 0
    
    def test_search_files_regex_invalid(self, project_folder):
        """Test invalid regex pattern."""
        result = project_folder.search_files(r"[invalid(regex", is_regex=True)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Invalid regex' in result['error']
    
    def test_search_files_no_matches(self, project_folder):
        """Test search with no matches."""
        result = project_folder.search_files("NONEXISTENT_STRING_12345")
        
        assert result['success'] is True
        assert result['count'] == 0
        assert result['matches'] == []
    
    def test_search_files_specific_pattern(self, project_folder):
        """Test search with specific file pattern."""
        result = project_folder.search_files("def", file_pattern="*.py")
        
        assert result['success'] is True
        assert result['count'] > 0
        
        # All matches should be from .py files
        for match in result['matches']:
            assert match['file'].endswith('.py')
    
    def test_search_files_unicode(self, project_folder):
        """Test search for Unicode characters."""
        result = project_folder.search_files("世界")
        
        assert result['success'] is True
        assert result['count'] > 0


class TestFindPythonDefinition:
    """Tests for find_python_definition() functionality."""
    
    def test_find_function_definition(self, project_folder):
        """Test finding function definition."""
        result = project_folder.find_python_definition("function_one", def_type="def")
        
        assert result['success'] is True
        assert result['count'] == 1
        
        defn = result['definitions'][0]
        assert defn['name'] == 'function_one'
        assert defn['file'] == 'test.py'
        assert defn['start_line'] == 1
        assert len(defn['text'].splitlines()) == 4  # Shall include definition, docstring, return, and trailing comment
        assert 'def function_one' in defn['text']
        assert 'return 1' in defn['text']
        # Trailing comment is included as it follows code line indentation
        assert 'Trailing comment' in defn['text'] 
    
    def test_find_class_definition(self, project_folder):
        """Test finding class definition."""
        result = project_folder.find_python_definition("MyClass", def_type="class")
        
        assert result['success'] is True
        assert result['count'] == 1
        
        defn = result['definitions'][0]
        assert defn['name'] == 'MyClass'
        assert 'class MyClass' in defn['text']
        assert 'def __init__' in defn['text']
        assert 'def method_one' in defn['text']
    
    def test_find_method_definition(self, project_folder):
        """Test finding method definition (indented def)."""
        result = project_folder.find_python_definition("method_one", def_type="def")
        
        assert result['success'] is True
        assert result['count'] == 1
        
        defn = result['definitions'][0]
        assert defn['name'] == 'method_one'
        assert 'def method_one' in defn['text']
    
    def test_find_definition_any_type(self, project_folder):
        """Test finding definition without specifying type."""
        result = project_folder.find_python_definition("MyClass"
                                                       )
        
        assert result['success'] is True
        assert result['count'] >= 1  # Could match class
    
    def test_find_definition_multiple_files(self, project_folder):
        """Test finding definitions across multiple files."""
        # Create another file with same function name
        project_folder.create_file("other.py", "def function_one():\n    pass")
        
        result = project_folder.find_python_definition("function_one", def_type="def")
        
        assert result['success'] is True
        assert result['count'] == 2
    
    def test_find_definition_nonexistent(self, project_folder):
        """Test finding non-existent definition."""
        result = project_folder.find_python_definition("nonexistent_function")
        
        assert result['success'] is True
        assert result['count'] == 0
        assert result['definitions'] == []
    
    def test_find_nested_class(self, project_folder):
        """Test finding class in subdirectory."""
        result = project_folder.find_python_definition("NestedClass", def_type="class")
        
        assert result['success'] is True
        assert result['count'] == 1
        
        defn = result['definitions'][0]
        assert 'subdir' in defn['file']


class TestIndentationParser:
    """Tests for Python indentation parsing helpers."""
    
    def test_get_indentation_spaces(self, project_folder):
        """Test indentation calculation with spaces."""
        assert project_folder._get_indentation("    code") == 4
        assert project_folder._get_indentation("  code") == 2
        assert project_folder._get_indentation("code") == 0
    
    def test_get_indentation_tabs(self, project_folder):
        """Test indentation calculation with tabs."""
        assert project_folder._get_indentation("\tcode") == 4
        assert project_folder._get_indentation("\t\tcode") == 8
    
    def test_get_indentation_mixed(self, project_folder):
        """Test indentation with mixed spaces and tabs."""
        assert project_folder._get_indentation("\t  code") == 6
    
    def test_find_def_end_simple(self, project_folder):
        """Test finding end of simple function."""
        lines = [
            "def foo():",
            "    return 1",
            "def bar():",
            "    return 2"
        ]
        
        end_idx = project_folder._find_def_end(lines, 0, 0)
        assert end_idx == 1
    
    def test_find_def_end_with_nested(self, project_folder):
        """Test finding end with nested structures."""
        lines = [
            "def outer():",
            "    def inner():",
            "        return 1",
            "    return 2",
            "def next():",
            "    pass"
        ]
        
        end_idx = project_folder._find_def_end(lines, 0, 0)
        assert end_idx == 3
    
    def test_find_def_end_with_comments(self, project_folder):
        """Test finding end with comments and empty lines."""
        lines = [
            "def foo():",
            "    # comment",
            "    ",
            "    return 1",
            "",
            "# trailing comment",
            "def bar():"
        ]
        
        end_idx = project_folder._find_def_end(lines, 0, 0)
        assert end_idx == 3  # Should stop at 'return 1', not include trailing empty/comments


class TestHelperFunctions:
    """Tests for helper response formatting functions."""
    
    def test_error_response(self, project_folder):
        """Test error response formatting."""
        result = project_folder._error_response("Test error", extra="data")
        
        assert result['success'] is False
        assert result['error'] == "Test error"
        assert result['extra'] == "data"
    
    def test_success_response(self, project_folder):
        """Test success response formatting."""
        result = project_folder._success_response(data="value", count=5)
        
        assert result['success'] is True
        assert result['data'] == "value"
        assert result['count'] == 5
    
    def test_file_metadata(self, project_folder):
        """Test file metadata extraction."""
        file_path = project_folder.project_path / "simple.txt"
        metadata = project_folder._file_metadata(file_path)
        
        assert 'path' in metadata
        assert 'size_bytes' in metadata
        assert 'size_lines' in metadata
        assert metadata['path'] == 'simple.txt'
        assert metadata['size_lines'] == 3


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_file_with_no_newline_at_end(self, temp_project):
        """Test handling file with no newline at end."""
        file_path = Path(temp_project) / "no_newline.txt"
        with open(file_path, 'w') as f:
            f.write("Line 1\nLine 2")  # No newline at end
        
        pf = ProjectFolder(temp_project)
        result = pf.load_file("no_newline.txt")
        
        assert result['success'] is True
        assert result['content'] == "Line 1\nLine 2"
    
    def test_file_with_only_newlines(self, temp_project):
        """Test file with only newlines."""
        file_path = Path(temp_project) / "newlines.txt"
        with open(file_path, 'w') as f:
            f.write("\n\n\n")
        
        pf = ProjectFolder(temp_project)
        result = pf.get_line_range("newlines.txt", 1, 3)
        
        assert result['success'] is True
        assert all(line == "" for line in result['lines'])
    
    def test_deeply_nested_path(self, temp_project):
        """Test operations on deeply nested path."""
        pf = ProjectFolder(temp_project)
        
        deep_path = "a/b/c/d/e/deep.txt"
        result = pf.create_file(deep_path, "Deep content")
        
        assert result['success'] is True
        
        # Verify we can load it
        result = pf.load_file(deep_path)
        assert result['success'] is True
        assert result['content'] == "Deep content"
    
    def test_file_with_very_long_lines(self, temp_project):
        """Test handling files with very long lines."""
        pf = ProjectFolder(temp_project)
        
        long_line = "x" * 10000
        content = f"Short\n{long_line}\nShort"
        
        result = pf.create_file("long_lines.txt", content)
        assert result['success'] is True
        
        result = pf.load_file("long_lines.txt")
        assert result['success'] is True
        assert long_line in result['content']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
