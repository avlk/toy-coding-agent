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
    
    def test_validate_path_rejects_absolute_path(self, project_folder):
        """Test that absolute paths are rejected."""
        abs_path = project_folder.project_path / "simple.txt"
        with pytest.raises(ProjectFolderError, match="Absolute paths are not allowed"):
            project_folder._validate_path(str(abs_path))
    
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
        with pytest.raises(ProjectFolderError, match="Absolute paths are not allowed"):
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
        metadata = project_folder.get_metadata(file_path)
        assert metadata['size_lines'] == 3
    
    def test_metadata_empty_file(self, project_folder):
        """Test line counting for empty file."""
        file_path = project_folder.project_path / "empty.txt"
        metadata = project_folder.get_metadata(file_path)
        assert metadata['size_lines'] == 0
    
    def test_metadata_uses_cache(self, project_folder):
        """Test that metadata is cached."""
        file_path = project_folder.project_path / "simple.txt"
        
        # First call - should cache
        metadata1 = project_folder.get_metadata(file_path)
        assert str("simple.txt") in project_folder._metadata_cache
        
        # Second call - should use cache
        metadata2 = project_folder.get_metadata(file_path)
        assert metadata1 == metadata2
    
    def test_metadata_invalidates_on_modification(self, project_folder):
        """Test that cache is invalidated when file is modified."""
        file_path = project_folder.project_path / "simple.txt"
        
        # Get initial count
        metadata1 = project_folder.get_metadata(file_path)
        assert metadata1['size_lines'] == 3
        
        # Modify file
        import time
        time.sleep(0.01)  # Ensure mtime changes
        with open(file_path, 'a') as f:
            f.write("\nLine 4")
        
        # Should detect change and recount
        metadata2 = project_folder.get_metadata(file_path)
        assert metadata2['size_lines'] == 4
    
    def testget_metadata_nonexistent_file(self, project_folder):
        """Test metadata for non-existent file returns error."""
        file_path = project_folder.project_path / "nonexistent.txt"
        metadata = project_folder.get_metadata(file_path)
        assert metadata['error'] is not None

class TestListFiles:
    """Tests for list_files() functionality."""
    
    def test_list_files_basic(self, project_folder):
        """Test basic file listing."""
        files = project_folder.list_files()
        
        assert isinstance(files, list)
        assert len(files) > 0
        
        # Check that files are present
        file_paths = [f['path'] for f in files]
        assert 'simple.txt' in file_paths
        assert 'test.py' in file_paths
    
    def test_list_files_includes_metadata(self, project_folder):
        """Test that file metadata is included."""
        files = project_folder.list_files()
        
        for file_info in files:
            assert 'path' in file_info
            assert 'size_bytes' in file_info
            assert 'size_lines' in file_info
            assert file_info['size_bytes'] >= 0
            assert file_info['size_lines'] >= 0
    
    def test_list_files_with_pattern(self, project_folder):
        """Test file listing with glob pattern."""
        files = project_folder.list_files(pattern="*.py")
        
        file_paths = [f['path'] for f in files]
        
        # Should include Python files
        assert any('test.py' in p for p in file_paths)
        assert any('nested.py' in p for p in file_paths)
        
        # Should not include text files
        assert not any('.txt' in p for p in file_paths)
    
    def test_list_files_sorted(self, project_folder):
        """Test that files are sorted by path."""
        files = project_folder.list_files()
        
        paths = [f['path'] for f in files]
        assert paths == sorted(paths)
    
    def test_list_files_empty_directory(self):
        """Test listing files in empty directory."""
        temp_dir = tempfile.mkdtemp()
        try:
            pf = ProjectFolder(temp_dir)
            files = pf.list_files()
            
            assert isinstance(files, list)
            assert len(files) == 0
        finally:
            shutil.rmtree(temp_dir)


class TestLoadFile:
    """Tests for load_file() functionality."""
    
    def test_load_file_basic(self, project_folder):
        """Test basic file loading."""
        result = project_folder.load_file("simple.txt")
        
        assert 'content' in result
        assert result['content'] == ["Line 1", "Line 2", "Line 3"]
        assert 'metadata' in result
    
    def test_load_file_with_unicode(self, project_folder):
        """Test loading file with Unicode content."""
        result = project_folder.load_file("unicode.txt")
        
        content_str = '\n'.join(result['content'])
        assert "世界" in content_str
        assert "🌍" in content_str
    
    def test_load_file_empty(self, project_folder):
        """Test loading empty file."""
        result = project_folder.load_file("empty.txt")
        
        assert result['content'] == []
    
    def test_load_file_with_subdirectory(self, project_folder):
        """Test loading file from subdirectory."""
        result = project_folder.load_file("subdir/data.txt")
        
        assert "Hello" in result['content']
        assert "World" in result['content']
    
    def test_load_file_nonexistent(self, project_folder):
        """Test loading non-existent file."""
        with pytest.raises(ProjectFolderError, match="not found"):
            project_folder.load_file("nonexistent.txt")
    
    def test_load_file_directory(self, project_folder):
        """Test attempting to load a directory."""
        with pytest.raises(ProjectFolderError, match="not a file"):
            project_folder.load_file("subdir")
    
    def test_load_file_path_traversal(self, project_folder):
        """Test that path traversal is blocked."""
        with pytest.raises(ProjectFolderError, match="outside the project folder"):
            project_folder.load_file("../outside.txt")


class TestCreateFile:
    """Tests for create_file() functionality."""
    
    def test_create_file_basic(self, project_folder):
        """Test basic file creation."""
        result = project_folder.create_file("new.txt", "New content")
        
        assert result['status'] == 'success'
        assert 'metadata' in result
        assert result['metadata']['path'] == 'new.txt'
        
        # Verify file exists
        file_path = project_folder.project_path / "new.txt"
        assert file_path.exists()
        with open(file_path, 'r') as f:
            assert f.read() == "New content"
    
    def test_create_file_with_subdirectory(self, project_folder):
        """Test creating file with new subdirectory."""
        result = project_folder.create_file("newdir/newfile.txt", "Content")
        
        assert result['status'] == 'success'
        assert 'metadata' in result
        
        # Verify file and directory exist
        file_path = project_folder.project_path / "newdir" / "newfile.txt"
        assert file_path.exists()
        assert file_path.parent.is_dir()
    
    def test_create_file_fails_if_exists(self, project_folder):
        """Test that creating file fails if it already exists."""
        # Try to create a file that already exists
        result = project_folder.create_file("simple.txt", "New content")
        
        assert result['status'] == 'error'
        assert result['error'] == 'file_exists'
        assert 'already exists' in result['message']
        
        # Verify original content is preserved
        file_path = project_folder.project_path / "simple.txt"
        with open(file_path, 'r') as f:
            assert f.read() == "Line 1\nLine 2\nLine 3"
    
    def test_create_file_with_overwrite(self, project_folder):
        """Test that creating file with overwrite=True replaces existing."""
        result = project_folder.create_file("simple.txt", "New content", overwrite=True)
        
        assert result['status'] == 'success'
        assert 'metadata' in result
        
        # Verify content is overwritten
        file_path = project_folder.project_path / "simple.txt"
        with open(file_path, 'r') as f:
            assert f.read() == "New content"
    
    def test_create_file_updates_cache(self, project_folder):
        """Test that creating file with overwrite updates cache with new line count."""
        file_name = "simple.txt"
        file_path = project_folder.project_path / file_name
        
        # Cache the file (original has 3 lines)
        old_metadata = project_folder.get_metadata(file_path)
        assert old_metadata['size_lines'] == 3
        assert file_name in project_folder._metadata_cache
        
        # Create/overwrite file with 4 lines
        result = project_folder.create_file(file_name, "New\nContent\nWith\nLines", overwrite=True)
        
        assert result['status'] == 'success'
        
        # Cache should have new count
        new_metadata = project_folder.get_metadata(file_path)
        assert new_metadata['size_lines'] == 4
    
    def test_create_file_path_traversal(self, project_folder):
        """Test that path traversal is blocked."""
        result = project_folder.create_file("../outside.txt", "Content")
        
        assert result['status'] == 'error'
        assert result['error'] == 'validation_error'
        assert 'outside the project folder' in result['message']
    
    def test_create_file_with_empty_content(self, project_folder):
        """Test creating file with empty content."""
        result = project_folder.create_file("empty_new.txt", "")
        
        assert result['status'] == 'success'
        assert 'metadata' in result
        file_path = project_folder.project_path / "empty_new.txt"
        assert file_path.exists()
        assert file_path.stat().st_size == 0
    
    def test_create_file_with_list_of_lines(self, project_folder):
        """Test creating file with list of lines."""
        lines = ["Line 1", "Line 2", "Line 3"]
        result = project_folder.create_file("list_test.txt", lines)
        
        assert result['status'] == 'success'
        assert result['metadata']['path'] == 'list_test.txt'
        
        # Verify file content using load_file
        load_result = project_folder.load_file("list_test.txt")
        assert load_result['content'] == lines
    
    def test_create_file_round_trip(self, project_folder):
        """Test load -> modify -> save round trip with list of lines."""
        # Load existing file
        result = project_folder.load_file("simple.txt")
        lines = result['content']
        
        # Modify
        lines[1] = "Modified Line 2"
        
        # Save back
        create_result = project_folder.create_file("modified.txt", lines)
        assert create_result['status'] == 'success'
        
        # Verify changes
        result2 = project_folder.load_file("modified.txt")
        assert result2['content'] == ["Line 1", "Modified Line 2", "Line 3"]
    
    def test_create_file_no_change(self, project_folder):
        """Test that overwriting with unchanged content returns no_change status."""
        # First create a file
        original_content = "Test content\nWith multiple lines\n"
        result1 = project_folder.create_file("test_unchanged.txt", original_content)
        assert result1['status'] == 'success'
        
        # Now overwrite with the exact same content
        result2 = project_folder.create_file("test_unchanged.txt", original_content, overwrite=True)
        assert result2['status'] == 'no_change'
        assert 'unchanged' in result2['message'].lower()
        assert 'metadata' in result2
        
        # Verify file content is still correct
        file_path = project_folder.project_path / "test_unchanged.txt"
        with open(file_path, 'r') as f:
            assert f.read() == original_content


class TestRemoveFile:
    """Tests for remove_file() functionality."""
    
    def test_remove_file_basic(self, project_folder):
        """Test basic file removal."""
        path = project_folder.remove_file("simple.txt")
        
        assert isinstance(path, str)
        assert path == "simple.txt"
        
        # Verify file is removed
        file_path = project_folder.project_path / "simple.txt"
        assert not file_path.exists()
    
    def test_remove_file_from_subdirectory(self, project_folder):
        """Test removing file from subdirectory."""
        path = project_folder.remove_file("subdir/data.txt")
        
        assert isinstance(path, str)
        
        file_path = project_folder.project_path / "subdir" / "data.txt"
        assert not file_path.exists()
    
    def test_remove_file_clears_cache(self, project_folder):
        """Test that removing file clears cache."""
        file_name = "simple.txt"
        file_path = project_folder.project_path / file_name
        
        # Cache the file
        project_folder.get_metadata(file_path)
        assert file_name in project_folder._metadata_cache
        
        # Remove file
        project_folder.remove_file(file_name)
        
        # Cache should be cleared
        assert file_name not in project_folder._metadata_cache
    
    def test_remove_file_nonexistent(self, project_folder):
        """Test removing non-existent file."""
        with pytest.raises(ProjectFolderError, match="not found"):
            project_folder.remove_file("nonexistent.txt")
    
    def test_remove_file_directory(self, project_folder):
        """Test attempting to remove a directory."""
        with pytest.raises(ProjectFolderError, match="not a file"):
            project_folder.remove_file("subdir")
    
    def test_remove_file_path_traversal(self, project_folder):
        """Test that path traversal is blocked."""
        with pytest.raises(ProjectFolderError, match="outside the project folder"):
            project_folder.remove_file("../outside.txt")


class TestGetLineRange:
    """Tests for get_line_range() functionality."""
    
    def test_get_line_range_basic(self, project_folder):
        """Test basic line range extraction."""
        result = project_folder.get_line_range("simple.txt", 1, 2)
        
        assert 'lines' in result
        assert result['lines'] == ["Line 1", "Line 2"]
        assert result['start_line'] == 1
        assert result['end_line'] == 2
    
    def test_get_line_range_single_line(self, project_folder):
        """Test extracting single line."""
        result = project_folder.get_line_range("simple.txt", 2, 2)
        
        assert result['lines'] == ["Line 2"]
    
    def test_get_line_range_all_lines(self, project_folder):
        """Test extracting all lines."""
        result = project_folder.get_line_range("simple.txt", 1, 3)
        
        assert len(result['lines']) == 3
    
    def test_get_line_range_beyond_file(self, project_folder):
        """Test range that extends beyond file length."""
        result = project_folder.get_line_range("simple.txt", 2, 100)
        
        assert result['end_line'] == 3  # Adjusted to file length
        assert len(result['lines']) == 2
    
    def test_get_line_range_invalid_start(self, project_folder):
        """Test invalid start line (< 1)."""
        with pytest.raises(ProjectFolderError, match="must be >= 1"):
            project_folder.get_line_range("simple.txt", 0, 2)
    
    def test_get_line_range_invalid_order(self, project_folder):
        """Test end_line < start_line."""
        with pytest.raises(ProjectFolderError, match="must be >= start_line"):
            project_folder.get_line_range("simple.txt", 3, 1)
    
    def test_get_line_range_start_beyond_file(self, project_folder):
        """Test start_line beyond file length."""
        with pytest.raises(ProjectFolderError, match="exceeds file length"):
            project_folder.get_line_range("simple.txt", 100, 200)
    
    def test_get_line_range_empty_file(self, project_folder):
        """Test getting lines from empty file."""
        with pytest.raises(ProjectFolderError, match="exceeds file length"):
            project_folder.get_line_range("empty.txt", 1, 1)


class TestSearchFiles:
    """Tests for search_files() functionality."""
    
    def test_search_files_basic(self, project_folder):
        """Test basic string search."""
        matches = project_folder.search_files("Line", file_pattern="*.txt")
        
        assert isinstance(matches, list)
        assert len(matches) > 0
        
        # Check match structure
        for match in matches:
            assert 'file' in match
            assert 'line_number' in match
            assert 'line' in match
            assert 'Line' in match['line']
    
    def test_search_files_case_insensitive(self, project_folder):
        """Test case-insensitive search."""
        matches = project_folder.search_files("LINE", case_sensitive=False, file_pattern="*.txt")
        
        assert len(matches) > 0
    
    def test_search_files_case_sensitive(self, project_folder):
        """Test case-sensitive search."""
        matches = project_folder.search_files("LINE", case_sensitive=True, file_pattern="*.txt")
        
        assert len(matches) == 0  # Should not match "Line"
    
    def test_search_files_regex(self, project_folder):
        """Test regex search."""
        matches = project_folder.search_files(r"Line \d+", is_regex=True, file_pattern="*.txt")
        
        assert len(matches) > 0
    
    def test_search_files_regex_invalid(self, project_folder):
        """Test invalid regex pattern."""
        with pytest.raises(ProjectFolderError, match="Invalid regex"):
            project_folder.search_files(r"[invalid(regex", is_regex=True)
    
    def test_search_files_no_matches(self, project_folder):
        """Test search with no matches."""
        matches = project_folder.search_files("NONEXISTENT_STRING_12345")
        
        assert isinstance(matches, list)
        assert len(matches) == 0
    
    def test_search_files_specific_pattern(self, project_folder):
        """Test search with specific file pattern."""
        matches = project_folder.search_files("def", file_pattern="*.py")
        
        assert len(matches) > 0
        
        # All matches should be from .py files
        for match in matches:
            assert match['file'].endswith('.py')
    
    def test_search_files_unicode(self, project_folder):
        """Test search for Unicode characters."""
        matches = project_folder.search_files("世界")
        
        assert len(matches) > 0


class TestFindPythonDefinition:
    """Tests for find_python_definition() functionality."""
    
    def test_find_function_definition(self, project_folder):
        """Test finding function definition."""
        definitions = project_folder.find_python_definition("function_one", def_type="def")
        
        assert isinstance(definitions, list)
        assert len(definitions) == 1
        
        defn = definitions[0]
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
        definitions = project_folder.find_python_definition("MyClass", def_type="class")
        
        assert isinstance(definitions, list)
        assert len(definitions) == 1
        
        defn = definitions[0]
        assert defn['name'] == 'MyClass'
        assert 'class MyClass' in defn['text']
        assert 'def __init__' in defn['text']
        assert 'def method_one' in defn['text']
    
    def test_find_method_definition(self, project_folder):
        """Test finding method definition (indented def)."""
        definitions = project_folder.find_python_definition("method_one", def_type="def")
        
        assert isinstance(definitions, list)
        assert len(definitions) == 1
        
        defn = definitions[0]
        assert defn['name'] == 'method_one'
        assert 'def method_one' in defn['text']
    
    def test_find_definition_any_type(self, project_folder):
        """Test finding definition without specifying type."""
        definitions = project_folder.find_python_definition("MyClass")
        
        assert isinstance(definitions, list)
        assert len(definitions) >= 1  # Could match class
    
    def test_find_definition_multiple_files(self, project_folder):
        """Test finding definitions across multiple files."""
        # Create another file with same function name
        project_folder.create_file("other.py", "def function_one():\n    pass", overwrite=True)
        
        definitions = project_folder.find_python_definition("function_one", def_type="def")
        
        assert isinstance(definitions, list)
        assert len(definitions) == 2
    
    def test_find_definition_nonexistent(self, project_folder):
        """Test finding non-existent definition."""
        definitions = project_folder.find_python_definition("nonexistent_function")
        
        assert isinstance(definitions, list)
        assert len(definitions) == 0
    
    def test_find_nested_class(self, project_folder):
        """Test finding class in subdirectory."""
        definitions = project_folder.find_python_definition("NestedClass", def_type="class")
        
        assert isinstance(definitions, list)
        assert len(definitions) == 1
        
        defn = definitions[0]
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
    
    def testget_metadata(self, project_folder):
        """Test file metadata extraction."""
        file_path = project_folder.project_path / "simple.txt"
        metadata = project_folder.get_metadata(file_path)
        
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
        
        assert result['content'] == ["Line 1", "Line 2"]
    
    def test_file_with_only_newlines(self, temp_project):
        """Test file with only newlines."""
        file_path = Path(temp_project) / "newlines.txt"
        with open(file_path, 'w') as f:
            f.write("\n\n\n")
        
        pf = ProjectFolder(temp_project)
        result = pf.get_line_range("newlines.txt", 1, 3)
        
        assert all(line == "" for line in result['lines'])
    
    def test_deeply_nested_path(self, temp_project):
        """Test operations on deeply nested path."""
        pf = ProjectFolder(temp_project)
        
        deep_path = "a/b/c/d/e/deep.txt"
        result = pf.create_file(deep_path, "Deep content")
        
        assert result['status'] == 'success'
        assert 'metadata' in result
        assert result['metadata']['path'] == deep_path
        
        # Verify we can load it
        load_result = pf.load_file(deep_path)
        assert load_result['content'] == ["Deep content"]
    
    def test_file_with_very_long_lines(self, temp_project):
        """Test handling files with very long lines."""
        pf = ProjectFolder(temp_project)
        
        long_line = "x" * 10000
        content = f"Short\n{long_line}\nShort"
        
        result = pf.create_file("long_lines.txt", content)
        assert result['status'] == 'success'
        assert 'metadata' in result
        
        load_result = pf.load_file("long_lines.txt")
        assert long_line in load_result['content']


class TestReplaceInFiles:
    """Tests for replace_in_files method."""
    
    def test_replace_in_files_substring(self, project_folder):
        """Test substring replacement across multiple files."""
        # Create test files
        project_folder.create_file("file1.txt", "foo bar foo")
        project_folder.create_file("file2.txt", "foo baz")
        project_folder.create_file("file3.txt", "no match here")
        
        # Perform replacement
        results = project_folder.replace_in_files("foo", "XXX", is_regex=False)
        
        # Check results
        assert len(results) == 2
        assert "file1.txt" in results
        assert "file2.txt" in results
        assert results["file1.txt"] == 2  # Two occurrences
        assert results["file2.txt"] == 1  # One occurrence
        
        # Verify file contents
        file1 = project_folder.load_file("file1.txt")
        assert file1['content'] == ["XXX bar XXX"]
        
        file2 = project_folder.load_file("file2.txt")
        assert file2['content'] == ["XXX baz"]
        
        file3 = project_folder.load_file("file3.txt")
        assert file3['content'] == ["no match here"]
    
    def test_replace_in_files_regex(self, project_folder):
        """Test regex replacement across files."""
        project_folder.create_file("code1.py", "value = 123")
        project_folder.create_file("code2.py", "count = 456")
        
        results = project_folder.replace_in_files(r"\d+", "NUM", is_regex=True, file_pattern="code*.py")
        
        assert len(results) == 2
        assert results["code1.py"] == 1
        assert results["code2.py"] == 1
        
        code1 = project_folder.load_file("code1.py")
        assert code1['content'] == ["value = NUM"]
    
    def test_replace_in_files_with_file_pattern(self, project_folder):
        """Test replacement with file pattern filter."""
        project_folder.create_file("mytest.py", "foo bar")
        project_folder.create_file("mytest.txt", "foo bar")
        project_folder.create_file("mytest.md", "foo bar")
        
        # Only replace in .py files
        results = project_folder.replace_in_files("foo", "XXX", file_pattern="**/*.py")
        
        assert len(results) == 1
        assert "mytest.py" in results
        
        # Verify other files unchanged
        txt = project_folder.load_file("mytest.txt")
        assert txt['content'] == ["foo bar"]
    
    def test_replace_in_files_no_matches(self, project_folder):
        """Test replacement when no matches found."""
        project_folder.create_file("test.txt", "hello world")
        
        results = project_folder.replace_in_files("foo", "bar")
        
        assert len(results) == 0
    
    def test_replace_in_files_invalid_regex(self, project_folder):
        """Test that invalid regex raises error."""
        with pytest.raises(ProjectFolderError, match="Invalid regex pattern"):
            project_folder.replace_in_files("[invalid", "test", is_regex=True)
    
    def test_replace_in_files_multiple_lines(self, project_folder):
        """Test replacement across multiple lines in same file."""
        project_folder.create_file("multi.txt", "line1 foo\nline2 foo\nline3 bar")
        
        results = project_folder.replace_in_files("foo", "XXX")
        
        assert results["multi.txt"] == 2
        
        content = project_folder.load_file("multi.txt")
        assert content['content'] == ["line1 XXX", "line2 XXX", "line3 bar"]


class TestMultilineReplaceInFile:
    """Tests for multiline_replace_in_file method."""
    
    def test_multiline_replace_basic(self, project_folder):
        """Test basic multiline replacement."""
        project_folder.create_file("test.txt", "line1\nline2\nline3\nline4")
        
        result = project_folder.multiline_replace_in_file(
            "test.txt",
            ["line2", "line3"],
            ["replaced"]
        )
        
        assert result == 1
        
        content = project_folder.load_file("test.txt")
        assert content['content'] == ["line1", "replaced", "line4"]
    
    def test_multiline_replace_multiple_matches(self, project_folder):
        """Test multiline replacement with multiple matches."""
        project_folder.create_file("test.txt", "a\nb\nc\na\nb\nc")
        
        result = project_folder.multiline_replace_in_file(
            "test.txt",
            ["a", "b"],
            ["x"]
        )
        
        assert result == 2
        
        content = project_folder.load_file("test.txt")
        assert content['content'] == ["x", "c", "x", "c"]
    
    def test_multiline_replace_with_only_around_line(self, project_folder):
        """Test multiline replacement with only_around_line parameter."""
        project_folder.create_file("test.txt", "a\nb\nc\na\nb\nc\na\nb")
        
        # Matches at lines 1, 4, 7; closest to line 5 is line 4
        result = project_folder.multiline_replace_in_file(
            "test.txt",
            ["a", "b"],
            ["x"],
            only_around_line=5
        )
        
        assert result == 1
        
        content = project_folder.load_file("test.txt")
        assert content['content'] == ["a", "b", "c", "x", "c", "a", "b"]
    
    def test_multiline_replace_no_matches(self, project_folder):
        """Test multiline replacement when no matches found."""
        project_folder.create_file("test.txt", "line1\nline2\nline3")
        
        result = project_folder.multiline_replace_in_file(
            "test.txt",
            ["line5", "line6"],
            ["replaced"]
        )
        
        assert result == 0
        
        # Verify file unchanged
        content = project_folder.load_file("test.txt")
        assert content['content'] == ["line1", "line2", "line3"]
    
    def test_multiline_replace_file_not_found(self, project_folder):
        """Test multiline replacement on non-existent file."""
        with pytest.raises(ProjectFolderError, match="File not found"):
            project_folder.multiline_replace_in_file(
                "nonexistent.txt",
                ["a"],
                ["b"]
            )
    
    def test_multiline_replace_expands_content(self, project_folder):
        """Test multiline replacement that expands content."""
        project_folder.create_file("test.txt", "line1\nline2\nline3")
        
        result = project_folder.multiline_replace_in_file(
            "test.txt",
            ["line2"],
            ["new1", "new2", "new3"]
        )
        
        assert result == 1
        
        content = project_folder.load_file("test.txt")
        assert content['content'] == ["line1", "new1", "new2", "new3", "line3"]
    
    def test_multiline_replace_deletes_content(self, project_folder):
        """Test multiline replacement that deletes content."""
        project_folder.create_file("test.txt", "line1\nline2\nline3\nline4")
        
        result = project_folder.multiline_replace_in_file(
            "test.txt",
            ["line2", "line3"],
            []
        )
        
        assert result == 1
        
        content = project_folder.load_file("test.txt")
        assert content['content'] == ["line1", "line4"]
    
    def test_multiline_replace_exact_match_required(self, project_folder):
        """Test that multiline replacement requires exact match."""
        project_folder.create_file("test.txt", "line1\nline2 extra\nline3")
        
        result = project_folder.multiline_replace_in_file(
            "test.txt",
            ["line2", "line3"],
            ["replaced"]
        )
        
        # Should not match because "line2" != "line2 extra"
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
