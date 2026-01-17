import unittest
from patch import multiline_replace
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)


class TestMultilineReplace(unittest.TestCase):
    
    def test_simple_single_line_replacement(self):
        """Test replacing a single line."""
        code_lines = ["a", "b", "c"]
        result = multiline_replace(code_lines, ["b"], ["x"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "x", "c"])
    
    def test_multi_line_multiline_replace(self):
        """Test replacing multiple consecutive lines."""
        code_lines = ["a", "b", "c", "d"]
        result = multiline_replace(code_lines, ["b", "c"], ["x", "y"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "x", "y", "d"])
    
    def test_multiple_non_overlapping_matches(self):
        """Test multiple separate matches."""
        code_lines = ["a", "b", "a", "b", "c"]
        result = multiline_replace(code_lines, ["a", "b"], ["x"])
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["x", "x", "c"])
    
    def test_non_overlapping_matches_discussed_case(self):
        """Test the case we discussed: {a,a,a,a,a} with search {a,a} should give 2 matches."""
        code_lines = ["a", "a", "a", "a", "a"]
        result = multiline_replace(code_lines, ["a", "a"], ["b"])
        self.assertEqual(result, 2, "Should find 2 non-overlapping matches")
        self.assertEqual(code_lines, ["b", "b", "a"])
    
    def test_no_matches_found(self):
        """Test when search pattern is not found."""
        code_lines = ["a", "b", "c"]
        result = multiline_replace(code_lines, ["x"], ["y"])
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, ["a", "b", "c"])
    
    def test_empty_search_string(self):
        """Test with empty search pattern."""
        code_lines = ["a", "b", "c"]
        result = multiline_replace(code_lines, [], ["x"])
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, ["a", "b", "c"])
    
    def test_search_longer_than_code(self):
        """Test when search pattern is longer than code_lines."""
        code_lines = ["a", "b"]
        result = multiline_replace(code_lines, ["a", "b", "c"], ["x"])
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, ["a", "b"])
    
    def test_replace_with_empty_list(self):
        """Test replacing with empty list (deletion)."""
        code_lines = ["a", "b", "c", "d"]
        result = multiline_replace(code_lines, ["b", "c"], [])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "d"])
    
    def test_replace_with_longer_sequence(self):
        """Test replacing with longer sequence."""
        code_lines = ["a", "b", "c"]
        result = multiline_replace(code_lines, ["b"], ["x", "y", "z"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "x", "y", "z", "c"])
    
    def test_replace_entire_code(self):
        """Test replacing entire code_lines."""
        code_lines = ["a", "b", "c"]
        result = multiline_replace(code_lines, ["a", "b", "c"], ["x"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["x"])
    
    def test_consecutive_different_patterns(self):
        """Test with consecutive but different patterns that don't overlap."""
        code_lines = ["a", "b", "b", "c"]
        result = multiline_replace(code_lines, ["b", "b"], ["x"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "x", "c"])
    
    def test_match_at_end(self):
        """Test match at the end of code_lines."""
        code_lines = ["a", "b", "c", "d"]
        result = multiline_replace(code_lines, ["c", "d"], ["x"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "b", "x"])
    
    def test_match_at_start(self):
        """Test match at the start of code_lines."""
        code_lines = ["a", "b", "c", "d"]
        result = multiline_replace(code_lines, ["a", "b"], ["x"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["x", "c", "d"])
    
    def test_prevent_recursive_matching(self):
        """Test that we don't recursively match our own replacements."""
        # Search for "b" and replace with "a,b"
        # Should only match the original "b", not the newly added "b"
        code_lines = ["a", "b", "c"]
        result = multiline_replace(code_lines, ["b"], ["a", "b"])
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "a", "b", "c"])
    
    def test_all_same_elements(self):
        """Test with all identical elements."""
        code_lines = ["a", "a", "a", "a"]
        result = multiline_replace(code_lines, ["a"], ["b"])
        self.assertEqual(result, 4)
        self.assertEqual(code_lines, ["b", "b", "b", "b"])
    
    def test_empty_code_lines(self):
        """Test with empty code_lines."""
        code_lines = []
        result = multiline_replace(code_lines, ["a"], ["b"])
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, [])
    
    def test_only_around_line_closest_match(self):
        """Test only_around_line parameter selects closest match."""
        code_lines = ["a", "b", "c", "a", "b", "c", "a", "b", "c"]
        # Matches at lines 0, 3, 6; closest to line 4 is line 3
        result = multiline_replace(code_lines, ["a", "b"], ["x"], only_around_line=4)
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "b", "c", "x", "c", "a", "b", "c"])
    
    def test_only_around_line_exact_match(self):
        """Test only_around_line when target line is an exact match."""
        code_lines = ["a", "b", "c", "a", "b", "c"]
        # Matches at lines 0, 3; target is 3
        result = multiline_replace(code_lines, ["a", "b"], ["x"], only_around_line=3)
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "b", "c", "x", "c"])
    
    def test_only_around_line_first_match(self):
        """Test only_around_line selects first match when it's closest."""
        code_lines = ["a", "b", "c", "d", "a", "b"]
        # Matches at lines 0, 4; closest to line 1 is line 0
        result = multiline_replace(code_lines, ["a", "b"], ["x"], only_around_line=1)
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["x", "c", "d", "a", "b"])
    
    def test_only_around_line_last_match(self):
        """Test only_around_line selects last match when it's closest."""
        code_lines = ["a", "b", "c", "d", "a", "b"]
        # Matches at lines 0, 4; closest to line 5 is line 4
        result = multiline_replace(code_lines, ["a", "b"], ["x"], only_around_line=5)
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["a", "b", "c", "d", "x"])
    
    def test_only_around_line_no_matches(self):
        """Test only_around_line when no matches exist."""
        code_lines = ["a", "b", "c"]
        result = multiline_replace(code_lines, ["x"], ["y"], only_around_line=1)
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, ["a", "b", "c"])
    
    def test_only_around_line_tie_prefers_earlier(self):
        """Test only_around_line when two matches are equidistant."""
        code_lines = ["a", "b", "c", "d", "a", "b"]
        # Matches at lines 0, 4; both are distance 2 from line 2
        # min() will pick the first one (0) when there's a tie
        result = multiline_replace(code_lines, ["a", "b"], ["x"], only_around_line=2)
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["x", "c", "d", "a", "b"])


if __name__ == "__main__":
    unittest.main()
