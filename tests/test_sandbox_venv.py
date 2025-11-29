import os
import shutil
import tempfile
import pytest
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sandbox_execution import execute_sandboxed

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

    def test_firejail_venv_package(self):
        self._run_and_check_package('firejail', 'requests')

    def test_docker_venv_package(self):
        import shutil
        if not shutil.which('docker'):
            pytest.skip('docker is not installed')
        try:
            subprocess.run(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            pytest.skip('docker is not usable in this environment')
        self._run_and_check_package('docker', 'requests')

    def test_bubblewrap_venv_package(self):
        import shutil
        if not shutil.which('bwrap'):
            pytest.skip('bubblewrap (bwrap) is not installed')
        self._run_and_check_package('bubblewrap', 'requests')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
