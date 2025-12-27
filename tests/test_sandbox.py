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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
