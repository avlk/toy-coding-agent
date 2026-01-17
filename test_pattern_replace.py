import unittest
from patch import pattern_replace
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)


class TestPatternReplace(unittest.TestCase):
    
    def test_simple_substring_replacement(self):
        """Test simple substring replacement."""
        code_lines = ["hello world", "goodbye world"]
        result = pattern_replace(code_lines, "world", "universe", is_regex=False)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["hello universe", "goodbye universe"])
    
    def test_multiple_matches_per_line_substring(self):
        """Test multiple substring matches in a single line."""
        code_lines = ["foo bar foo baz foo"]
        result = pattern_replace(code_lines, "foo", "XXX", is_regex=False)
        self.assertEqual(result, 3)
        self.assertEqual(code_lines, ["XXX bar XXX baz XXX"])
    
    def test_multiple_matches_per_line_regex(self):
        """Test multiple regex matches in a single line."""
        code_lines = ["abc123def456ghi789"]
        result = pattern_replace(code_lines, r"\d+", "NUM", is_regex=True)
        self.assertEqual(result, 3)
        self.assertEqual(code_lines, ["abcNUMdefNUMghiNUM"])
    
    def test_regex_word_boundaries(self):
        """Test regex with word boundaries."""
        code_lines = ["foo foobar barfoo foo"]
        result = pattern_replace(code_lines, r"\bfoo\b", "XXX", is_regex=True)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["XXX foobar barfoo XXX"])
    
    def test_no_matches(self):
        """Test when pattern is not found."""
        code_lines = ["hello world", "goodbye world"]
        result = pattern_replace(code_lines, "universe", "cosmos", is_regex=False)
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, ["hello world", "goodbye world"])
    
    def test_empty_pattern(self):
        """Test with empty pattern."""
        code_lines = ["hello world"]
        result = pattern_replace(code_lines, "", "X", is_regex=False)
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, ["hello world"])
    
    def test_empty_code_lines(self):
        """Test with empty code_lines."""
        code_lines = []
        result = pattern_replace(code_lines, "hello", "hi", is_regex=False)
        self.assertEqual(result, 0)
        self.assertEqual(code_lines, [])
    
    def test_partial_line_matches(self):
        """Test that only some lines match."""
        code_lines = ["foo bar", "baz qux", "foo baz"]
        result = pattern_replace(code_lines, "foo", "XXX", is_regex=False)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["XXX bar", "baz qux", "XXX baz"])
    
    def test_regex_special_characters(self):
        """Test regex with special characters."""
        code_lines = ["a.b.c", "a_b_c", "abc"]
        result = pattern_replace(code_lines, r"\.", "_", is_regex=True)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["a_b_c", "a_b_c", "abc"])
    
    def test_regex_groups_and_backreferences(self):
        """Test regex with capture groups."""
        code_lines = ["function foo()", "function bar()"]
        result = pattern_replace(code_lines, r"function (\w+)", r"def \1", is_regex=True)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["def foo()", "def bar()"])
    
    def test_substring_vs_regex_difference(self):
        """Test that substring mode treats regex chars as literals."""
        code_lines = ["a.b.c"]
        # Substring mode: . is literal
        result = pattern_replace(code_lines, ".", "X", is_regex=False)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["aXbXc"])
        
        # Reset and try regex mode
        code_lines = ["a.b.c"]
        result = pattern_replace(code_lines, r"\.", "X", is_regex=True)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["aXbXc"])
    
    def test_replace_entire_line(self):
        """Test replacing entire line content."""
        code_lines = ["old_line", "another_old_line"]
        result = pattern_replace(code_lines, "old_line", "new_line", is_regex=False)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["new_line", "another_new_line"])
    
    def test_empty_replacement(self):
        """Test replacing with empty string (deletion)."""
        code_lines = ["hello world", "goodbye world"]
        result = pattern_replace(code_lines, " world", "", is_regex=False)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["hello", "goodbye"])
    
    def test_case_sensitive_substring(self):
        """Test that substring replacement is case sensitive."""
        code_lines = ["Hello World", "hello world"]
        result = pattern_replace(code_lines, "hello", "hi", is_regex=False)
        self.assertEqual(result, 1)
        self.assertEqual(code_lines, ["Hello World", "hi world"])
    
    def test_regex_case_insensitive_flag(self):
        """Test regex with case insensitive flag using inline modifier."""
        code_lines = ["Hello World", "hello world"]
        result = pattern_replace(code_lines, r"(?i)hello", "hi", is_regex=True)
        self.assertEqual(result, 2)
        self.assertEqual(code_lines, ["hi World", "hi world"])


if __name__ == "__main__":
    unittest.main()
