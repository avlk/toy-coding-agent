"""
Unit tests for patch.py module.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from patch import (
    is_unified_diff, is_unified_diff_no_counts,
    Hunk, extract_hunks, patch_code, patch_project
)
import tempfile
import os


class TestIsUnifiedDiff:
    """Tests for is_unified_diff() function."""
    
    def test_valid_unified_diff(self):
        patch = [
            "--- a/file.py",
            "+++ b/file.py",
            "@@ -1,3 +1,3 @@",
            " line1",
            "-line2",
            "+line2_modified",
            " line3"
        ]
        assert is_unified_diff(patch) == True
    
    def test_unified_diff_no_counts(self):
        patch = [
            "@@ ... @@",
            "-old line",
            "+new line"
        ]
        assert is_unified_diff(patch) == True
    
    def test_not_unified_diff(self):
        patch = [
            "just some text",
            "without diff headers"
        ]
        assert is_unified_diff(patch) == False
    
    def test_empty_patch(self):
        assert is_unified_diff([]) == False


class TestIsUnifiedDiffNoCounts:
    """Tests for is_unified_diff_no_counts() function."""
    
    def test_has_no_counts(self):
        patch = ["@@ ... @@"]
        assert is_unified_diff_no_counts(patch) == True
    
    def test_has_counts(self):
        patch = ["@@ -1,3 +1,3 @@"]
        assert is_unified_diff_no_counts(patch) == False


class TestHunk:
    """Tests for Hunk class."""
    
    def test_simple_replacement(self):
        header = "@@ -5,3 +5,3 @@"
        lines = [
            " context_before",
            "-old_line",
            "+new_line",
            " context_after"
        ]
        hunk = Hunk(header, lines)
        
        assert hunk.start_original == 5
        assert hunk.start_new == 5
        assert hunk.match_count() == 3
        assert hunk.replace_count() == 3
        assert hunk.match == ["context_before", "old_line", "context_after"]
        assert hunk.replace == ["context_before", "new_line", "context_after"]
    
    def test_addition(self):
        header = "@@ -5,2 +5,3 @@"
        lines = [
            " context",
            "+new_line",
            " more_context"
        ]
        hunk = Hunk(header, lines)
        
        assert hunk.match_count() == 2
        assert hunk.replace_count() == 3
    
    def test_deletion(self):
        header = "@@ -5,3 +5,2 @@"
        lines = [
            " context",
            "-deleted_line",
            " more_context"
        ]
        hunk = Hunk(header, lines)
        
        assert hunk.match_count() == 3
        assert hunk.replace_count() == 2
    
    def test_empty_hunk(self):
        header = "@@ -5,0 +5,0 @@"
        lines = []
        hunk = Hunk(header, lines)
        
        assert hunk.empty() == True
    
    def test_faulty_llm_patch_without_space(self):
        """Test handling of LLM-generated patch without leading space."""
        header = "@@ -1,2 +1,2 @@"
        lines = [
            "context_line",  # Missing leading space
            "-old",
            "+new"
        ]
        hunk = Hunk(header, lines)
        
        assert "context_line" in hunk.match
        assert "context_line" in hunk.replace
    
    def test_excessive_context_trimming(self):
        """Test trimming of excessive context lines."""
        header = "@@ -1,10 +1,10 @@"
        lines = [
            " ctx1", " ctx2", " ctx3", " ctx4", " ctx5",  # 5 leading context
            "-old",
            "+new",
            " ctx6", " ctx7", " ctx8", " ctx9", " ctx10"  # 5 trailing context
        ]
        hunk = Hunk(header, lines)
        
        # Should trim to MAX_STARTING_CONTEXT (3) and MAX_TRAILING_CONTEXT (3)
        assert hunk.match_count() <= 7  # 3 + 1 + 3
    
    def test_matches_code_exact(self):
        header = "@@ -1,2 +1,2 @@"
        lines = ["-old_line", "+new_line"]
        hunk = Hunk(header, lines)
        
        code_lines = ["old_line", "other"]
        assert hunk.matches_code(code_lines, 0, fuzziness=0) == True
        assert hunk.matches_code(code_lines, 1, fuzziness=0) == False
    
    def test_matches_code_with_comment_fuzziness(self):
        header = "@@ -1,1 +1,1 @@"
        lines = ["-code_line"]
        hunk = Hunk(header, lines)
        
        code_lines = ["code_line  # with comment"]
        assert hunk.matches_code(code_lines, 0, fuzziness=0) == False
        assert hunk.matches_code(code_lines, 0, fuzziness=1) == True
    
    def test_match_code_finds_location(self):
        header = "@@ -1,2 +1,2 @@"
        lines = ["-line2", "-line3"]
        hunk = Hunk(header, lines)
        
        code_lines = ["line1", "line2", "line3", "line4"]
        match_index = hunk.match_code(code_lines, fuzziness=0)
        assert match_index == 1


class TestExtractHunks:
    """Tests for extract_hunks() function."""
    
    def test_single_hunk(self):
        patch = [
            "--- a/file.py",
            "+++ b/file.py",
            "@@ -1,2 +1,2 @@",
            " context",
            "-old",
            "+new"
        ]
        hunks = extract_hunks(patch)
        
        assert len(hunks) == 1
        assert hunks[0].match_count() == 2
    
    def test_multiple_hunks(self):
        patch = [
            "@@ -1,2 +1,2 @@",
            "-old1",
            "+new1",
            "@@ -10,2 +10,2 @@",
            "-old2",
            "+new2"
        ]
        hunks = extract_hunks(patch)
        
        assert len(hunks) == 2
    
    def test_hunks_separated_by_file_markers(self):
        patch = [
            "@@ -1,1 +1,1 @@",
            "-old",
            "---",
            "@@ -5,1 +5,1 @@",
            "+new"
        ]
        hunks = extract_hunks(patch)
        
        assert len(hunks) == 2


class TestPatchCode:
    """Tests for patch_code() function."""
    
    def test_simple_patch(self):
        code_lines = ["line1", "line2", "line3"]
        patch_lines = [
            "@@ -2,1 +2,1 @@",
            "-line2",
            "+line2_modified"
        ]
        
        result = patch_code(code_lines, patch_lines, fuzziness=0)
        
        assert result == True
        assert code_lines == ["line1", "line2_modified", "line3"]
    
    def test_multiple_hunks(self):
        code_lines = ["a", "b", "c", "d"]
        patch_lines = [
            "@@ -1,1 +1,1 @@",
            "-a",
            "+A",
            "@@ -3,1 +3,1 @@",
            "-c",
            "+C"
        ]
        
        result = patch_code(code_lines, patch_lines, fuzziness=0)
        
        assert result == True
        assert code_lines == ["A", "b", "C", "d"]
    
    def test_failed_patch(self):
        code_lines = ["line1", "line2"]
        patch_lines = [
            "@@ -1,1 +1,1 @@",
            "-nonexistent",
            "+new"
        ]
        
        result = patch_code(code_lines, patch_lines, fuzziness=0)
        
        assert result == False
        assert code_lines == ["line1", "line2"]  # Unchanged
    
    def test_patch_with_fuzziness(self):
        code_lines = ["line1  # comment", "line2"]
        patch_lines = [
            "@@ -1,1 +1,1 @@",
            "-line1",
            "+line1_new"
        ]
        
        # Should fail with fuzziness=0
        code_lines_copy = code_lines.copy()
        result = patch_code(code_lines_copy, patch_lines, fuzziness=0)
        assert result == False
        
        # Should succeed with fuzziness=1
        result = patch_code(code_lines, patch_lines, fuzziness=1)
        assert result == True
        assert code_lines[0] == "line1_new"
    
    def test_insertion(self):
        code_lines = ["line1", "line3"]
        patch_lines = [
            "@@ -1,1 +1,2 @@",
            " line1",
            "+line2",
        ]
        
        result = patch_code(code_lines, patch_lines, fuzziness=0)
        
        assert result == True
        assert code_lines == ["line1", "line2", "line3"]
    
    def test_deletion(self):
        code_lines = ["line1", "line2", "line3"]
        patch_lines = [
            "@@ -1,2 +1,1 @@",
            " line1",
            "-line2"
        ]
        
        result = patch_code(code_lines, patch_lines, fuzziness=0)
        
        assert result == True
        assert code_lines == ["line1", "line3"]


class TestPatchProject:
    """Tests for patch_project() function."""
    
    def test_single_file_patch(self):
        """Test patching a single file in a project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create a test file
            test_file = project_dir / "test.py"
            test_file.write_text("line1\nline2\nline3\n")
            
            # Create a patch
            patch_lines = [
                "--- a/test.py",
                "+++ b/test.py",
                "@@ -2,1 +2,1 @@",
                "-line2",
                "+line2_modified"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            content = test_file.read_text()
            assert "line2_modified" in content
            assert "line2\n" not in content
    
    def test_multiple_files_patch(self):
        """Test patching multiple files in one patch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create test files
            file1 = project_dir / "file1.py"
            file1.write_text("a\nb\nc\n")
            
            file2 = project_dir / "file2.py"
            file2.write_text("x\ny\nz\n")
            
            # Create a patch for both files
            patch_lines = [
                "--- a/file1.py",
                "+++ b/file1.py",
                "@@ -2,1 +2,1 @@",
                "-b",
                "+B",
                "--- a/file2.py",
                "+++ b/file2.py",
                "@@ -2,1 +2,1 @@",
                "-y",
                "+Y"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            assert "B" in file1.read_text()
            assert "Y" in file2.read_text()
    
    def test_nested_directory_structure(self):
        """Test patching files in nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create nested directory structure
            subdir = project_dir / "src" / "module"
            subdir.mkdir(parents=True)
            
            test_file = subdir / "code.py"
            test_file.write_text("def foo():\n    pass\n")
            
            # Create a patch with nested path
            patch_lines = [
                "--- a/src/module/code.py",
                "+++ b/src/module/code.py",
                "@@ -1,2 +1,2 @@",
                " def foo():",
                "-    pass",
                "+    return 42"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            content = test_file.read_text()
            assert "return 42" in content
    
    def test_security_path_outside_project(self):
        """Test that paths outside project directory are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Try to patch a file outside the project using ..
            patch_lines = [
                "--- a/../outside.py",
                "+++ b/../outside.py",
                "@@ -1,1 +1,1 @@",
                "-old",
                "+new"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            # Should fail due to security check
            assert result == False
    
    def test_nonexistent_file(self):
        """Test handling of patch for non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            patch_lines = [
                "--- a/nonexistent.py",
                "+++ b/nonexistent.py",
                "@@ -1,1 +1,1 @@",
                "-old",
                "+new"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == False
    
    def test_mixed_success_failure(self):
        """Test patch with some hunks succeeding and some failing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create test files
            good_file = project_dir / "good.py"
            good_file.write_text("line1\nline2\n")
            
            bad_file = project_dir / "bad.py"
            bad_file.write_text("different\ncontent\n")
            
            # Patch with one good and one bad hunk
            patch_lines = [
                "--- a/good.py",
                "+++ b/good.py",
                "@@ -1,1 +1,1 @@",
                "-line1",
                "+LINE1",
                "--- a/bad.py",
                "+++ b/bad.py",
                "@@ -1,1 +1,1 @@",
                "-nonexistent",
                "+new"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == False
            # Good file should still be patched
            assert "LINE1" in good_file.read_text()
            # Bad file should remain unchanged
            assert "different" in bad_file.read_text()
    
    def test_fuzziness_levels(self):
        """Test patch application with different fuzziness levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            test_file = project_dir / "test.py"
            test_file.write_text("code_line  # comment\n")
            
            patch_lines = [
                "--- a/test.py",
                "+++ b/test.py",
                "@@ -1,1 +1,1 @@",
                "-code_line",
                "+new_line"
            ]
            
            # Should fail with fuzziness=0
            test_file.write_text("code_line  # comment\n")
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            assert result == False
            
            # Should succeed with fuzziness=1
            test_file.write_text("code_line  # comment\n")
            result = patch_project(project_dir, patch_lines, fuzziness=1)
            assert result == True
            assert "new_line" in test_file.read_text()
    
    def test_multiple_hunks_same_file(self):
        """Test multiple hunks applied to the same file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            test_file = project_dir / "test.py"
            test_file.write_text("line1\nline2\nline3\nline4\n")
            
            patch_lines = [
                "--- a/test.py",
                "+++ b/test.py",
                "@@ -1,1 +1,1 @@",
                "-line1",
                "+LINE1",
                "@@ -3,1 +3,1 @@",
                "-line3",
                "+LINE3"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            content = test_file.read_text()
            assert "LINE1" in content
            assert "LINE3" in content
            assert "line2" in content
            assert "line4" in content
    
    def test_empty_patch(self):
        """Test with an empty patch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            result = patch_project(project_dir, [], fuzziness=0)
            
            # Should succeed (nothing to do)
            assert result == True
    
    def test_hunk_without_filename(self):
        """Test handling of hunks without filename information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Patch without file markers
            patch_lines = [
                "@@ -1,1 +1,1 @@",
                "-old",
                "+new"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            # Should succeed but skip hunks without filenames
            assert result == True
    
    def test_file_with_b_prefix_and_without(self):
        """Test parsing filenames with and without 'b/' prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create test files
            file1 = project_dir / "with_prefix.py"
            file1.write_text("a\n")
            
            file2 = project_dir / "without_prefix.py"
            file2.write_text("x\n")
            
            # Patch with both styles
            patch_lines = [
                "--- a/with_prefix.py",
                "+++ b/with_prefix.py",
                "@@ -1,1 +1,1 @@",
                "-a",
                "+A",
                "--- without_prefix.py",
                "+++ without_prefix.py",
                "@@ -1,1 +1,1 @@",
                "-x",
                "+X"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            assert "A" in file1.read_text()
            assert "X" in file2.read_text()
    
    def test_insertion_and_deletion(self):
        """Test patch with line insertions and deletions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            test_file = project_dir / "test.py"
            test_file.write_text("line1\nline2\nline3\n")
            
            # Insert after line1, delete line2
            patch_lines = [
                "--- a/test.py",
                "+++ b/test.py",
                "@@ -1,3 +1,3 @@",
                " line1",
                "+inserted",
                "-line2",
                " line3"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            content = test_file.read_text()
            assert "inserted" in content
            assert "line2" not in content
            assert content.count("line1") == 1
            assert content.count("line3") == 1
    
    def test_readonly_file_handling(self):
        """Test handling of read-only files (should fail gracefully)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            test_file = project_dir / "readonly.py"
            test_file.write_text("line1\n")
            
            # Make file read-only
            os.chmod(test_file, 0o444)
            
            patch_lines = [
                "--- a/readonly.py",
                "+++ b/readonly.py",
                "@@ -1,1 +1,1 @@",
                "-line1",
                "+LINE1"
            ]
            
            try:
                result = patch_project(project_dir, patch_lines, fuzziness=0)
                # Should fail due to write permission
                assert result == False
            finally:
                # Restore permissions for cleanup
                os.chmod(test_file, 0o644)
    
    def test_hunk_filename_storage(self):
        """Test that hunks correctly store their associated filename."""
        patch_lines = [
            "--- a/test.py",
            "+++ b/test.py",
            "@@ -1,1 +1,1 @@",
            "-old",
            "+new"
        ]
        
        hunks = extract_hunks(patch_lines)
        
        assert len(hunks) == 1
        assert hunks[0].filename == "test.py"
    
    def test_create_new_file(self):
        """Test creating a new file from patch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Patch to create a new file
            patch_lines = [
                "--- /dev/null",
                "+++ b/newfile.py",
                "@@ -0,0 +1,3 @@",
                "+def hello():",
                "+    print('Hello')",
                "+    return 42"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            new_file = project_dir / "newfile.py"
            assert new_file.exists()
            content = new_file.read_text()
            assert "def hello():" in content
            assert "print('Hello')" in content
            assert "return 42" in content
    
    def test_create_multiple_new_files(self):
        """Test creating multiple new files in one patch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            patch_lines = [
                "--- /dev/null",
                "+++ b/file1.py",
                "@@ -0,0 +1,2 @@",
                "+# File 1",
                "+x = 1",
                "--- /dev/null",
                "+++ b/file2.py",
                "@@ -0,0 +1,2 @@",
                "+# File 2",
                "+y = 2"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            file1 = project_dir / "file1.py"
            file2 = project_dir / "file2.py"
            assert file1.exists()
            assert file2.exists()
            assert "x = 1" in file1.read_text()
            assert "y = 2" in file2.read_text()
    
    def test_create_file_in_nested_directory(self):
        """Test creating a new file in non-existent nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            patch_lines = [
                "--- /dev/null",
                "+++ b/src/utils/helper.py",
                "@@ -0,0 +1,2 @@",
                "+def helper():",
                "+    pass"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            new_file = project_dir / "src" / "utils" / "helper.py"
            assert new_file.exists()
            assert "def helper():" in new_file.read_text()
    
    def test_mixed_create_and_modify(self):
        """Test patch that both creates new files and modifies existing ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            # Create an existing file
            existing_file = project_dir / "existing.py"
            existing_file.write_text("old_line\n")
            
            patch_lines = [
                "--- a/existing.py",
                "+++ b/existing.py",
                "@@ -1,1 +1,1 @@",
                "-old_line",
                "+new_line",
                "--- /dev/null",
                "+++ b/newfile.py",
                "@@ -0,0 +1,1 @@",
                "+fresh_content"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            assert result == True
            # Existing file should be modified
            assert "new_line" in existing_file.read_text()
            assert "old_line" not in existing_file.read_text()
            # New file should be created
            new_file = project_dir / "newfile.py"
            assert new_file.exists()
            assert "fresh_content" in new_file.read_text()
    
    def test_new_file_flag_detection(self):
        """Test that is_new_file flag is correctly set when parsing patches."""
        patch_lines = [
            "--- /dev/null",
            "+++ b/newfile.py",
            "@@ -0,0 +1,2 @@",
            "+line1",
            "+line2"
        ]
        
        hunks = extract_hunks(patch_lines)
        
        assert len(hunks) == 1
        assert hunks[0].is_new_file == True
        assert hunks[0].filename == "newfile.py"
    
    def test_existing_file_flag_not_set(self):
        """Test that is_new_file flag is False for regular patches."""
        patch_lines = [
            "--- a/existing.py",
            "+++ b/existing.py",
            "@@ -1,1 +1,1 @@",
            "-old",
            "+new"
        ]
        
        hunks = extract_hunks(patch_lines)
        
        assert len(hunks) == 1
        assert hunks[0].is_new_file == False
    
    def test_create_empty_file(self):
        """Test creating an empty file (edge case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            
            patch_lines = [
                "--- /dev/null",
                "+++ b/empty.txt",
                "@@ -0,0 +1,0 @@"
            ]
            
            result = patch_project(project_dir, patch_lines, fuzziness=0)
            
            # Should create the file even if empty
            assert result == True
            empty_file = project_dir / "empty.txt"
            assert empty_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
