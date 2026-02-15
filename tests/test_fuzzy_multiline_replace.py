import pytest
from patch import multiline_replace


def test_exact_match_at_target_line():
    """Test exact match at the specified around_line."""
    code_lines = [
        "def hello():",
        "    print('Hello')",
        "    return True",
        "",
        "def world():",
        "    print('World')",
    ]
    
    s_str = [
        "def hello():",
        "    print('Hello')",
        "    return True",
    ]
    
    r_str = [
        "def hello():",
        "    print('Hi there')",
        "    return False",
    ]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=0)
    
    assert result == 0
    assert code_lines[0] == "def hello():"
    assert code_lines[1] == "    print('Hi there')"
    assert code_lines[2] == "    return False"


def test_match_with_small_differences():
    """Test matching with minor differences (typos, spacing)."""
    code_lines = [
        "def calculate(x, y):",
        "    result = x + y",
        "    return result",
        "",
        "print('done')",
    ]
    
    # Search string has small differences
    s_str = [
        "def calculate(x,y):",  # Missing space after comma
        "    result = x+y",      # Missing spaces around +
        "    return result",
    ]
    
    r_str = [
        "def compute(a, b):",
        "    total = a + b",
        "    return total",
    ]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=0)
    
    assert result == 0
    assert code_lines[0] == "def compute(a, b):"
    assert code_lines[1] == "    total = a + b"
    assert code_lines[2] == "    return total"


def test_match_within_tolerance():
    """Test matching when target is within TOLERANCE range but not exact."""
    code_lines = [
        "# Header comment",
        "# Another comment",
        "",
        "def function():",
        "    pass",
        "",
        "# Footer",
    ]
    
    s_str = [
        "def function():",
        "    pass",
    ]
    
    r_str = [
        "def new_function():",
        "    return None",
    ]
    
    # Target line 1, but actual match at line 3 (within TOLERANCE=5)
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=None)
    
    assert result == 3
    assert code_lines[3] == "def new_function():"
    assert code_lines[4] == "    return None"


def test_no_match_distance_too_large():
    """Test that no match is found when Levenshtein distance exceeds MAX_DISTANCE."""
    code_lines = [
        "def hello():",
        "    print('Hello World')",
        "    return True",
    ]
    
    # Search for something completely different
    s_str = [
        "class MyClass:",
        "    def __init__(self):",
        "        self.x = 0",
    ]
    
    r_str = [
        "# Replacement",
    ]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=0)
    
    assert result is None
    # Code should remain unchanged
    assert code_lines[0] == "def hello():"
    assert code_lines[1] == "    print('Hello World')"


def test_no_match_outside_range():
    """Test that no match is found when match is outside TOLERANCE range."""
    code_lines = [
        "line 0",
        "line 1",
        "line 2",
        "line 3",
        "line 4",
        "line 5",
        "line 6",
        "line 7",
        "line 8",
        "line 9",
        "line 10",
        "target line",
        "line 12",
    ]
    
    s_str = ["target line"]
    r_str = ["replaced line"]
    
    # Search around lines 0..10, but match is at line 11
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=5)
    
    assert result is None
    assert code_lines[11] == "target line"  # Unchanged


def test_empty_search_string():
    """Test handling of empty search string."""
    code_lines = ["line 1", "line 2"]
    s_str = []
    r_str = ["replacement"]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=None)
    
    assert result is None  # Function returns None for empty search
    # Code should remain unchanged
    assert code_lines == ["line 1", "line 2"]


def test_single_line_replacement():
    """Test replacing a single line."""
    code_lines = [
        "import os",
        "import sys",
        "import json",
    ]
    
    s_str = ["import sys"]
    r_str = ["import subprocess"]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=None)
    
    assert result == 1
    assert code_lines == ["import os", "import subprocess", "import json"]


def test_multiline_with_varying_distances():
    """Test that function selects best match (lowest distance) when multiple candidates exist."""
    code_lines = [
        "def foo(x):",
        "    return x",
        "",
        "def foo(y):",  # Similar but slightly different
        "    return y",
        "",
        "def bar():",
        "    pass",
    ]
    
    s_str = [
        "def foo(x):",
        "    return x",
    ]
    
    r_str = [
        "def baz(x):",
        "    return x * 2",
    ]
    
    # Around line 2, should match the first function (lines 0-1, closer and exact)
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=None)
    
    assert result == 0
    assert code_lines[0] == "def baz(x):"
    assert code_lines[1] == "    return x * 2"
    # Second function should remain unchanged
    assert code_lines[3] == "def foo(y):"


def test_replacement_at_file_start():
    """Test replacement at the beginning of file."""
    code_lines = [
        "first line",
        "second line",
        "third line",
    ]
    
    s_str = ["first line"]
    r_str = ["new first line"]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=0)
    
    assert result == 0
    assert code_lines[0] == "new first line"


def test_replacement_at_file_end():
    """Test replacement at the end of file."""
    code_lines = [
        "first line",
        "second line",
        "last line",
    ]
    
    s_str = ["last line"]
    r_str = ["new last line"]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=None)
    
    assert result == 2
    assert code_lines[2] == "new last line"


def test_multiline_size_change():
    """Test replacing with different number of lines."""
    code_lines = [
        "def old():",
        "    pass",
        "",
        "print('after')",
    ]
    
    s_str = [
        "def old():",
        "    pass",
    ]
    
    r_str = [
        "def new():",
        "    x = 1",
        "    y = 2",
        "    return x + y",
    ]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=0)
    
    assert result == 0
    assert len(code_lines) == 6  # 4 new lines + 1 empty + 1 print
    assert code_lines[0] == "def new():"
    assert code_lines[3] == "    return x + y"
    assert code_lines[5] == "print('after')"


def test_whitespace_differences():
    """Test matching with whitespace differences."""
    code_lines = [
        "def func():",
        "    x = 1",
        "    return x",
    ]
    
    # Search with different indentation
    s_str = [
        "def func():",
        "   x = 1",  # 3 spaces instead of 4
        "    return x",
    ]
    
    r_str = [
        "def func():",
        "    y = 2",
        "    return y",
    ]
    
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=0)
    
    # Should still match due to small Levenshtein distance
    assert result == 0
    assert code_lines[1] == "    y = 2"


def test_prefers_better_match():
    """Test that function prefers match closer to around_line when distances are equal."""
    code_lines = [
        "line 0",
        "barget",  # Line 1
        "line 2",
        "line 3",
        "line 4",
        "tambet",  # Line 5
        "line 6",
    ]
    
    s_str = ["target"]
    r_str = ["replaced"]
    
    # Search around line 1, should match line 1 (not line 5)
    result = multiline_replace(code_lines, s_str, r_str, only_around_line=1)
    
    assert result == 1
    assert code_lines[1] == "replaced"
    assert code_lines[5] == "tambet"  # Unchanged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
