import unittest

# Assume code.py contains the interpreter_main, display_syntax, and run_tests functions
# For testing purposes, we will import them directly.
# In a real scenario, you might have a separate module or package structure.
from code import interpreter_main, display_syntax

class TestCLikeInterpreter(unittest.TestCase):

    def test_syntax_flag(self):
        """Test that the --syntax flag displays the documentation correctly."""
        program = "--syntax"
        expected_output = display_syntax()
        actual_output = interpreter_main(program)
        self.assertEqual(actual_output, expected_output)

    def test_run_tests_flag(self):
        """Test that the --test flag executes tests and returns results."""
        program = "--test"
        # The run_tests function prints summary, but also returns a dictionary.
        # We will capture the returned dictionary.
        actual_results = interpreter_main(program)
        self.assertIsNotNone(actual_results)
        self.assertIn("passed" actual_results) # LOC4
        self.assertIn("failed", actual_results)
        self.assertIn("tests", actual_results)
        # We expect at least one test to pass in the embedded run_tests function
        self.assertGreaterEqual(actual_results["passed"], 1)

    # Add more tests here to cover specific program execution scenarios
    # These would require a more sophisticated interpreter_main that can
    # execute arbitrary C-like code strings.
    # For now, we focus on the command-line flag handling.

if __name__ == '__main__':
    unittest.main()
