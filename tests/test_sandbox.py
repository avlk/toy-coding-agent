import os
import shutil
import tempfile
import pytest
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sandbox_execution import execute_sandboxed, sandbox_method_available

class TestSandboxBasic:
    """Basic tests for sandboxed code execution without venv."""

    def _run(self, method, code):
        return execute_sandboxed(
            code=code,
            timeout=30,
            method=method
        )

    def test_subprocess_basic(self):
        result = self._run('subprocess', 'print("hello sandbox")')
        assert result['success'], f"subprocess failed: {result['stderr']}"
        assert "hello sandbox" in result['stdout'], "subprocess did not produce expected output"

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_basic(self):
        result = self._run('firejail', 'print("hello sandbox")')
        assert result['success'], f"firejail failed: {result['stderr']}"
        assert "hello sandbox" in result['stdout'], "firejail did not produce expected output"

    @pytest.mark.skipif(not sandbox_method_available('docker'), reason="docker not available")
    def test_docker_basic(self):
        try:
            subprocess.run(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            pytest.skip('docker is not usable in this environment')
        result = self._run('docker', 'print("hello sandbox")')
        assert result['success'], f"docker failed: {result['stderr']}"
        assert "hello sandbox" in result['stdout'], "docker did not produce expected output"

    @pytest.mark.skipif(not sandbox_method_available('bubblewrap'), reason="bubblewrap not available")
    def test_bubblewrap_basic(self):
        result = self._run('bubblewrap', 'print("hello sandbox")')
        assert result['success'], f"bubblewrap failed: {result['stderr']}"
        assert "hello sandbox" in result['stdout'], "bubblewrap did not produce expected output"

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_file_protection(self):
        # Create a file outside the sandbox
        outside_file = os.path.abspath("protected_file.txt")
        with open(outside_file, "w") as f:
            f.write("protected content")

        # Python code that tries to overwrite the file
        code = f"with open(r'{outside_file}', 'w') as f: f.write('hacked')"
        result = self._run('firejail', code)
        with open(outside_file, "r") as f:
            content = f.read()
        os.remove(outside_file)
        assert content == "protected content", "firejail allowed file modification!"
        assert not result['success']

    @pytest.mark.skipif(not sandbox_method_available('bubblewrap'), reason="bubblewrap not available")
    def test_bubblewrap_file_protection(self):
        # Create a file outside the sandbox
        outside_file = os.path.abspath("protected_file.txt")
        with open(outside_file, "w") as f:
            f.write("protected content")

        # Python code that tries to overwrite the file
        code = f"with open(r'{outside_file}', 'w') as f: f.write('hacked')"
        result = self._run('bubblewrap', code)
        assert not result['success']
        with open(outside_file, "r") as f:
            content = f.read()
        os.remove(outside_file)
        assert content == "protected content", "bubblewrap allowed file modification!"

class TestSandboxVenv:
    """Tests for venv and package installation in sandboxed execution."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, request):
        temp_dir_name = "solutions/venv/test_venv"
        self.venv_dir = os.path.join(tempfile.gettempdir(), temp_dir_name)
        if os.path.exists(self.venv_dir):
            shutil.rmtree(self.venv_dir)
        def fin():
            shutil.rmtree(self.venv_dir, ignore_errors=True)
        request.addfinalizer(fin)

    def _run_and_check_package(self, method, package, import_name=None):
        code = f"import {import_name or package}\nprint({import_name or package}.__version__)"
        result = execute_sandboxed(
            code=code,
            timeout=60,
            method=method,
            venv_path=self.venv_dir,
            extra_packages=[package]
        )
        assert result['success'], f"{method} failed: {result['stderr']}"
        assert result['stdout'].strip(), f"{method} did not print version"

    def test_subprocess_venv_package(self):
        self._run_and_check_package('subprocess', 'requests')

    @pytest.mark.skipif(not sandbox_method_available('firejail'), reason="firejail not available")
    def test_firejail_venv_package(self):
        self._run_and_check_package('firejail', 'requests')

    @pytest.mark.skipif(not sandbox_method_available('docker'), reason="docker not available")
    def test_docker_venv_package(self):
        self._run_and_check_package('docker', 'requests')

    @pytest.mark.skipif(not sandbox_method_available('bubblewrap'), reason="bubblewrap not available")
    def test_bubblewrap_venv_package(self):
        self._run_and_check_package('bubblewrap', 'requests')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
