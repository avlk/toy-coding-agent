# Unit Tests for Coding Agent

This directory contains unit tests for the coding agent modules.

## Test Coverage

### Pure Logic Tests (No Mocking Required)
- **test_coding_agent.py**: Tests for core classes and pure functions
  - `Iteration` class tests
  - `Context` class tests  
  - `load_task_config()` tests
  - `progress_check()` tests
  - `format_final_code()` tests
  - `create_filename()` tests

### Utility Module Tests
- **test_utils.py**: Tests for `utils.py` module - string conversion, code cleaning, variant selection, etc.
- **test_token_tracker.py**: Tests for `token_tracker.py` module - token usage tracking and reporting
- **test_patch.py**: Tests for `patch.py` module - unified diff parsing and patching

## Running Tests

### Using VS Code Test Explorer

The workspace is configured to use the official Python extension's built-in test runner for pytest.

**To access the Test Explorer:**
- Look for the Testing icon (beaker/flask icon) in the Activity Bar (left sidebar)
- Or press `Ctrl+Shift+T` to toggle the Test Explorer
- Or use Command Palette (`Ctrl+Shift+P`) → "Test: Focus on Test Explorer View"
- Or go to menu: `View` → `Testing`

**Features:**
- Tests are auto-discovered when you save files
- Click the play button next to any test or test class to run it
- See results inline with green checkmarks or red X's
- Debug tests by clicking the debug icon next to them
- View test output in the Output panel

**Requirements:**
- Python extension (`ms-python.python`) - already installed
- Configuration is in `.vscode/settings.json`

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

## Dependencies

- pytest >= 9.0.1

Install with:
```bash
pip install pytest python-Levenshtein
```
