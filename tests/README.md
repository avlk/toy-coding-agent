# Unit Tests for Coding Agent

This directory contains unit tests for the coding agent modules.

## Test Coverage

- **test_utils.py**: Tests for `utils.py` module (string conversion, code cleaning, variant selection, etc.)
- **test_token_tracker.py**: Tests for `token_tracker.py` module (token usage tracking and reporting)
- **test_patch.py**: Tests for `patch.py` module (unified diff parsing and patching)

## Running Tests

### Using VS Code
1. Open the Testing panel (beaker icon in the sidebar)
2. Tests will be auto-discovered
3. Click the play button next to any test or test class to run it
4. Use CodeLens "Run Test" links above each test function

### Using Command Line
```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_utils.py -v

# Run specific test class
pytest tests/test_utils.py::TestToLines -v

# Run specific test
pytest tests/test_utils.py::TestToLines::test_none_input -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=html
```

## Test Statistics

- **Total tests**: 66
- **test_utils.py**: 30 tests
- **test_token_tracker.py**: 11 tests
- **test_patch.py**: 24 tests
- **All passing**: ✓

## Dependencies

- pytest >= 9.0.1

Install with:
```bash
pip install pytest python-Levenshtein
```
