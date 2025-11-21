"""
Unit tests for utils.py module.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    to_lines, to_string, select_variant, format_goals,
    clean_code_block, code_quality_gate
)


class TestToLines:
    """Tests for to_lines() function."""
    
    def test_none_input(self):
        assert to_lines(None) == []
    
    def test_list_input(self):
        input_list = ["line1", "line2", "line3"]
        assert to_lines(input_list) == input_list
    
    def test_string_input(self):
        assert to_lines("line1\nline2\nline3") == ["line1", "line2", "line3"]
    
    def test_empty_string(self):
        assert to_lines("") == []
    
    def test_single_line(self):
        assert to_lines("single line") == ["single line"]


class TestToString:
    """Tests for to_string() function."""
    
    def test_none_input(self):
        assert to_string(None) == ""
    
    def test_string_input(self):
        assert to_string("test string") == "test string"
    
    def test_list_input(self):
        assert to_string(["line1", "line2", "line3"]) == "line1\nline2\nline3"
    
    def test_empty_list(self):
        assert to_string([]) == ""
    
    def test_single_item_list(self):
        assert to_string(["single"]) == "single"


class TestSelectVariant:
    """Tests for select_variant() function."""
    
    def test_variant_a(self):
        lines = [
            "common line",
            "?a variant a line",
            "?b variant b line",
            "another common"
        ]
        result = select_variant(lines, "a")
        assert result == ["common line", "variant a line", "another common"]
    
    def test_variant_b(self):
        lines = [
            "common line",
            "?a variant a line",
            "?b variant b line",
            "another common"
        ]
        result = select_variant(lines, "b")
        assert result == ["common line", "variant b line", "another common"]
    
    def test_no_variants(self):
        lines = ["line1", "line2", "line3"]
        result = select_variant(lines, "a")
        assert result == lines
    
    def test_mixed_variants(self):
        lines = [
            "?a only in a",
            "?b only in b",
            "common",
            "?a another a",
        ]
        result = select_variant(lines, "a")
        assert result == ["only in a", "common", "another a"]


class TestFormatGoals:
    """Tests for format_goals() function."""
    
    def test_list_without_bullets(self):
        goals = ["goal 1", "goal 2", "goal 3"]
        result = format_goals(goals)
        assert result == "- goal 1\n- goal 2\n- goal 3"
    
    def test_list_with_bullets(self):
        goals = ["- goal 1", "- goal 2", "- goal 3"]
        result = format_goals(goals)
        assert result == "- goal 1\n- goal 2\n- goal 3"
    
    def test_mixed_bullets(self):
        goals = ["goal 1", "- goal 2", "goal 3"]
        result = format_goals(goals)
        assert result == "- goal 1\n- goal 2\n- goal 3"
    
    def test_string_input(self):
        goals = "- goal 1\n- goal 2"
        result = format_goals(goals)
        # Should add bullets to non-bulleted lines
        assert "- goal 1" in result
        assert "- goal 2" in result
    
    def test_empty_list(self):
        assert format_goals([]) == ""


class TestCleanCodeBlock:
    """Tests for clean_code_block() function."""
    
    def test_triple_backticks(self):
        code = ["```python", "def foo():", "    pass", "```"]
        result = clean_code_block(code)
        assert result == ["def foo():", "    pass"]
    
    def test_triple_tildes(self):
        code = ["~~~python", "def foo():", "    pass", "~~~"]
        result = clean_code_block(code)
        assert result == ["def foo():", "    pass"]
    
    def test_no_markers(self):
        code = ["def foo():", "    pass"]
        result = clean_code_block(code)
        assert result == ["def foo():", "    pass"]
    
    def test_string_input(self):
        code = "```python\ndef foo():\n    pass\n```"
        result = clean_code_block(code)
        assert result == ["def foo():", "    pass"]
    
    def test_excessive_empty_lines(self):
        code = ["line1", "", "", "", "line2"]
        result = clean_code_block(code)
        assert result == ["line1", "", "", "line2"]
    
    def test_mixed_markers(self):
        code = ["```", "code", "~~~"]
        result = clean_code_block(code)
        assert result == ["code"]


class TestCodeQualityGate:
    """Tests for code_quality_gate() function."""
    
    def test_valid_code(self):
        code = ["def foo():", "    return 42", "", "print(foo())"]
        assert code_quality_gate(code) == True
    
    def test_line_too_long(self):
        code = ["x = '" + "a" * 3000 + "'"]
        assert code_quality_gate(code) == False
    
    def test_too_many_duplicate_lines(self):
        code = ["same line"] * 150
        assert code_quality_gate(code) == False
    
    def test_acceptable_duplicate_lines(self):
        code = ["same line"] * 50
        assert code_quality_gate(code) == True
    
    def test_empty_code(self):
        assert code_quality_gate([]) == True
    
    def test_string_input(self):
        code = "def foo():\n    return 42"
        assert code_quality_gate(code) == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
