import os
import shutil
import tempfile
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sandbox_execution import execute_sandboxed, sandbox_method_available


class TestSandboxBasic:
    """Basic tests for multi-file project execution."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request):
        """Create a temporary project directory for each test."""
        self.test_dir = tempfile.mkdtemp(prefix="test_project_")
        self.project_path = os.path.join(self.test_dir, "project")
        os.makedirs(self.project_path)
        
        def fin():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        request.addfinalizer(fin)

    def _create_simple_project(self):
        """Create a simple single-file project."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write('print("Hello from project!")\n')
    
    def _create_multifile_project(self):
        """Create a project with multiple files and imports."""
        # main.py
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("""
from utils import greet
from calculator import add

print(greet("World"))
print(f"2 + 3 = {add(2, 3)}")
""")
        
        # utils.py
        utils_py = os.path.join(self.project_path, "utils.py")
        with open(utils_py, "w") as f:
            f.write("""
def greet(name):
    return f"Hello, {name}!"
""")
        
        # calculator.py
        calc_py = os.path.join(self.project_path, "calculator.py")
        with open(calc_py, "w") as f:
            f.write("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")

    def _create_project_with_args(self):
        """Create a project that uses command-line arguments."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("""
import sys

print(f"Number of arguments: {len(sys.argv) - 1}")
for i, arg in enumerate(sys.argv[1:], 1):
    print(f"Arg {i}: {arg}")
""")

    def _create_project_with_requirements(self):
        """Create a project with requirements.txt."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("""
import requests
print(f"requests version: {requests.__version__}")
""")
        
        requirements_txt = os.path.join(self.project_path, "requirements.txt")
        with open(requirements_txt, "w") as f:
            f.write("requests\n")

    def test_subprocess_simple(self):
        """Test simple project execution with subprocess."""
        self._create_simple_project()
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        assert result['success'], f"subprocess failed: {result['stderr']}"
        assert "Hello from project!" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_simple(self):
        """Test simple project execution with firejail."""
        self._create_simple_project()
        result = execute_sandboxed(self.project_path, "main.py", method='firejail')
        assert result['success'], f"firejail failed: {result['stderr']}"
        assert "Hello from project!" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('docker'), reason="docker not available")
    def test_docker_simple(self):
        """Test simple project execution with docker."""
        self._create_simple_project()
        result = execute_sandboxed(self.project_path, "main.py", method='docker')
        assert result['success'], f"docker failed: {result['stderr']}"
        assert "Hello from project!" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('bubblewrap'), reason="bubblewrap not available")
    def test_bubblewrap_simple(self):
        """Test simple project execution with bubblewrap."""
        self._create_simple_project()
        result = execute_sandboxed(self.project_path, "main.py", method='bubblewrap')
        assert result['success'], f"bubblewrap failed: {result['stderr']}"
        assert "Hello from project!" in result['stdout']

    def test_subprocess_multifile(self):
        """Test multi-file project with imports."""
        self._create_multifile_project()
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        assert result['success'], f"subprocess failed: {result['stderr']}"
        assert "Hello, World!" in result['stdout']
        assert "2 + 3 = 5" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_multifile(self):
        """Test multi-file project with firejail."""
        self._create_multifile_project()
        result = execute_sandboxed(self.project_path, "main.py", method='firejail')
        assert result['success'], f"firejail failed: {result['stderr']}"
        assert "Hello, World!" in result['stdout']
        assert "2 + 3 = 5" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('bubblewrap'), reason="bubblewrap not available")
    def test_bubblewrap_multifile(self):
        """Test multi-file project with bubblewrap."""
        self._create_multifile_project()
        result = execute_sandboxed(self.project_path, "main.py", method='bubblewrap')
        assert result['success'], f"bubblewrap failed: {result['stderr']}"
        assert "Hello, World!" in result['stdout']
        assert "2 + 3 = 5" in result['stdout']

    def test_subprocess_with_args(self):
        """Test project execution with command-line arguments."""
        self._create_project_with_args()
        result = execute_sandboxed(self.project_path, "main.py --verbose test 123", method='subprocess')
        assert result['success'], f"subprocess failed: {result['stderr']}"
        assert "Number of arguments: 3" in result['stdout']
        assert "Arg 1: --verbose" in result['stdout']
        assert "Arg 2: test" in result['stdout']
        assert "Arg 3: 123" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_with_args(self):
        """Test project with args using firejail."""
        self._create_project_with_args()
        result = execute_sandboxed(self.project_path, "main.py arg1 arg2", method='firejail')
        assert result['success'], f"firejail failed: {result['stderr']}"
        assert "Number of arguments: 2" in result['stdout']

    def test_subprocess_with_requirements(self):
        """Test project with requirements.txt."""
        self._create_project_with_requirements()
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess', timeout=120)
        assert result['success'], f"subprocess failed: {result['stderr']}"
        assert "requests version:" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_with_requirements(self):
        """Test project with requirements using firejail."""
        self._create_project_with_requirements()
        result = execute_sandboxed(self.project_path, "main.py", method='firejail', timeout=120)
        assert result['success'], f"firejail failed: {result['stderr']}"
        assert "requests version:" in result['stdout']

    def test_auto_method_selection(self):
        """Test automatic sandbox method selection."""
        self._create_simple_project()
        result = execute_sandboxed(self.project_path, "main.py", method='auto')
        assert result['success'], f"auto method failed: {result['stderr']}"
        assert "Hello from project!" in result['stdout']
        assert result['method'] in ['firejail', 'docker', 'bubblewrap', 'subprocess']

    def test_nonexistent_project(self):
        """Test error handling for nonexistent project."""
        result = execute_sandboxed("/nonexistent/project", "main.py", method='subprocess')
        assert not result['success']
        assert "not found" in result['stderr'].lower()

    def test_nonexistent_entry_point(self):
        """Test error handling for nonexistent entry point."""
        os.makedirs(self.project_path, exist_ok=True)
        result = execute_sandboxed(self.project_path, "nonexistent.py", method='subprocess')
        assert not result['success']
        assert "not found" in result['stderr'].lower()

    def test_empty_cmd_args(self):
        """Test error handling for empty cmd_args."""
        self._create_simple_project()
        result = execute_sandboxed(self.project_path, "", method='subprocess')
        assert not result['success']
        assert "cannot be empty" in result['stderr']

    def test_syntax_error_in_project(self):
        """Test handling of syntax errors in project code."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("print('incomplete\n")
        
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        assert not result['success']
        assert "SyntaxError" in result['stderr'] or "EOL" in result['stderr']

    def test_runtime_error_in_project(self):
        """Test handling of runtime errors in project code."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("x = 1 / 0\n")
        
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        assert not result['success']
        assert "ZeroDivisionError" in result['stderr']

    def test_venv_reuse(self):
        """Test that venv is reused across multiple executions."""
        self._create_simple_project()
        
        # First execution - creates venv
        result1 = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        assert result1['success']
        venv_path = os.path.join(self.project_path, '.venv')
        assert os.path.exists(venv_path)
        
        # Second execution - reuses venv
        result2 = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        assert result2['success']
        assert "Hello from project!" in result2['stdout']


class TestSandboxAdvanced:
    """Advanced tests for project execution with nested structures."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request):
        """Create a temporary project directory for each test."""
        self.test_dir = tempfile.mkdtemp(prefix="test_project_advanced_")
        self.project_path = os.path.join(self.test_dir, "project")
        os.makedirs(self.project_path)
        
        def fin():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        request.addfinalizer(fin)

    def _create_nested_module_project(self):
        """Create a project with nested module structure."""
        # main.py
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("""
from lib.math_ops import calculate
from lib.string_ops import format_result

result = calculate(10, 5)
print(format_result(result))
""")
        
        # lib/__init__.py
        lib_dir = os.path.join(self.project_path, "lib")
        os.makedirs(lib_dir)
        with open(os.path.join(lib_dir, "__init__.py"), "w") as f:
            f.write("")
        
        # lib/math_ops.py
        with open(os.path.join(lib_dir, "math_ops.py"), "w") as f:
            f.write("""
def calculate(a, b):
    return a + b
""")
        
        # lib/string_ops.py
        with open(os.path.join(lib_dir, "string_ops.py"), "w") as f:
            f.write("""
def format_result(value):
    return f"Result: {value}"
""")

    def test_subprocess_nested_modules(self):
        """Test project with nested module structure."""
        self._create_nested_module_project()
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        assert result['success'], f"subprocess failed: {result['stderr']}"
        assert "Result: 15" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_nested_modules(self):
        """Test nested modules with firejail."""
        self._create_nested_module_project()
        result = execute_sandboxed(self.project_path, "main.py", method='firejail')
        assert result['success'], f"firejail failed: {result['stderr']}"
        assert "Result: 15" in result['stdout']

    @pytest.mark.skipif(not sandbox_method_available('bubblewrap'), reason="bubblewrap not available")
    def test_bubblewrap_nested_modules(self):
        """Test nested modules with bubblewrap."""
        self._create_nested_module_project()
        result = execute_sandboxed(self.project_path, "main.py", method='bubblewrap')
        assert result['success'], f"bubblewrap failed: {result['stderr']}"
        assert "Result: 15" in result['stdout']


class TestSandboxErrorDistinction:
    """Test proper distinction between sandbox errors and program failures."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request):
        """Create a temporary project directory for each test."""
        self.test_dir = tempfile.mkdtemp(prefix="test_sandbox_errors_")
        self.project_path = os.path.join(self.test_dir, "project")
        os.makedirs(self.project_path)
        
        def fin():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        request.addfinalizer(fin)

    def _create_exit_code_project(self, exit_code: int):
        """Create a project that exits with a specific code."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write(f"""
import sys
print("Program running")
sys.exit({exit_code})
""")

    def test_program_exits_with_zero(self):
        """Test program that exits with code 0 (success)."""
        self._create_exit_code_project(0)
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        
        assert result['success'] is True
        assert result['exit_code'] == 0
        assert result['sandbox_error'] is False
        assert "Program running" in result['stdout']

    def test_program_exits_with_one(self):
        """Test program that exits with code 1 (normal failure)."""
        self._create_exit_code_project(1)
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        
        assert result['success'] is False
        assert result['exit_code'] == 1
        assert result['sandbox_error'] is False  # Program ran, just failed
        assert "Program running" in result['stdout']

    def test_program_exits_with_minus_one(self):
        """Test program that exits with code -1 (should not be confused with sandbox error)."""
        self._create_exit_code_project(-1)
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        
        # Key test: exit code -1 from program should NOT be treated as sandbox error
        assert result['success'] is False
        assert result['exit_code'] == 255  # Note: Unix converts -1 to 255
        assert result['sandbox_error'] is False  # This is a program failure, not sandbox failure
        assert "Program running" in result['stdout']

    def test_program_exits_with_various_codes(self):
        """Test programs with various exit codes."""
        test_codes = [0, 1, 2, 42, 127]
        for code in test_codes:
            self._create_exit_code_project(code)
            result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
            
            assert result['exit_code'] == code, f"Exit code mismatch for {code}"
            assert result['sandbox_error'] is False, f"Code {code} incorrectly marked as sandbox error"
            assert "Program running" in result['stdout']

    def test_sandbox_setup_error_nonexistent_project(self):
        """Test that nonexistent project is marked as sandbox error."""
        result = execute_sandboxed("/nonexistent/path", "main.py", method='subprocess')
        
        assert result['success'] is False
        assert result['sandbox_error'] is True  # Setup error
        assert "not found" in result['stderr'].lower()

    def test_sandbox_setup_error_nonexistent_entry(self):
        """Test that nonexistent entry point is marked as sandbox error."""
        result = execute_sandboxed(self.project_path, "missing.py", method='subprocess')
        
        assert result['success'] is False
        assert result['sandbox_error'] is True  # Setup error
        assert "not found" in result['stderr'].lower()

    def test_sandbox_setup_error_empty_args(self):
        """Test that empty cmd_args is marked as sandbox error."""
        result = execute_sandboxed(self.project_path, "", method='subprocess')
        
        assert result['success'] is False
        assert result['sandbox_error'] is True  # Setup error
        assert "cannot be empty" in result['stderr']

    def test_sandbox_setup_error_unknown_method(self):
        """Test that unknown sandbox method is marked as sandbox error."""
        self._create_exit_code_project(0)
        result = execute_sandboxed(self.project_path, "main.py", method='nonexistent_method')
        
        assert result['success'] is False
        assert result['sandbox_error'] is True
        assert "Unknown sandbox method" in result['stderr']

    def test_auto_mode_stops_on_first_success(self):
        """Test that auto mode stops trying methods once sandbox succeeds, even if program fails."""
        # Create a program that will fail
        self._create_exit_code_project(1)
        
        result = execute_sandboxed(self.project_path, "main.py", method='auto')
        
        # Should succeed in running (sandbox worked) even though program exited with 1
        assert result['success'] is False  # Program failed
        assert result['exit_code'] == 1
        assert result['sandbox_error'] is False  # Sandbox worked fine
        assert "Program running" in result['stdout']
        # Should have used the first available method, not tried all of them
        assert result['method'] in ['firejail', 'docker', 'bubblewrap', 'subprocess']

    def test_auto_mode_with_program_exit_minus_one(self):
        """Test that auto mode doesn't retry when program exits with -1 equivalent."""
        # Create a program that will exit with -1
        self._create_exit_code_project(-1)
        
        result = execute_sandboxed(self.project_path, "main.py", method='auto')
        
        # Should not have tried multiple methods - first one should have succeeded in running
        assert result['sandbox_error'] is False  # Sandbox worked
        assert "Program running" in result['stdout']
        # Exit code will be 255 (Unix conversion of -1)
        assert result['exit_code'] == 255

    def test_runtime_error_not_sandbox_error(self):
        """Test that runtime errors in program are not marked as sandbox errors."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("""
print("Starting program")
x = 1 / 0
""")
        
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        
        assert result['success'] is False
        assert result['sandbox_error'] is False  # Program error, not sandbox error
        assert "ZeroDivisionError" in result['stderr']
        assert "Starting program" in result['stdout']

    def test_syntax_error_not_sandbox_error(self):
        """Test that syntax errors in program are not marked as sandbox errors."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("print('incomplete\n")
        
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        
        assert result['success'] is False
        assert result['sandbox_error'] is False  # Program error, not sandbox error
        assert "SyntaxError" in result['stderr'] or "EOL" in result['stderr']

    def test_import_error_not_sandbox_error(self):
        """Test that import errors are not marked as sandbox errors."""
        main_py = os.path.join(self.project_path, "main.py")
        with open(main_py, "w") as f:
            f.write("""
import nonexistent_module
print("This won't run")
""")
        
        result = execute_sandboxed(self.project_path, "main.py", method='subprocess')
        
        assert result['success'] is False
        assert result['sandbox_error'] is False  # Program error, not sandbox error
        assert "ModuleNotFoundError" in result['stderr'] or "ImportError" in result['stderr']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
