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
    Hunk, extract_hunks, patch_code
)


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
