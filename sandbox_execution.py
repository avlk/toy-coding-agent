"""
Sandboxed code execution implementations for the coding agent.
"""

import os
import subprocess
import tempfile
import shutil
import sys


def _make_result(success: bool, stdout: str, stderr: str, exit_code: int, method: str) -> dict:
    """Helper function to create consistent result dictionaries."""
    return {
        'success': success,
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code,
        'method': method
    }


# ==================== Sandbox Method Classes ====================

class FirejailMethod:
    """Firejail sandbox implementation."""
    
    name = 'firejail'
    
    @staticmethod
    def is_available() -> bool:
        """Check if firejail is available and properly configured."""
        if not shutil.which('firejail'):
            return False

        try:
            with open("/proc/version") as f:
                version = f.read().lower()
                if "microsoft" in version or "wsl" in version:
                    return False  # WSL kernel → namespaces incomplete
        except FileNotFoundError:
            pass

        # Check AppArmor
        if os.path.exists("/sys/module/apparmor/parameters/enabled"):
            with open("/sys/module/apparmor/parameters/enabled") as f:
                if f.read().strip() != "Y":
                    return False
        else:
            return False  # no AppArmor support

        # Check namespaces
        ns_path = "/proc/self/ns"
        if os.path.exists(ns_path):
            ns_entries = os.listdir(ns_path)
            if len(ns_entries) < 5:
                return False

        return True
    
    @staticmethod
    def execute(project_path: str, entry_file: str, args_list: list, venv_python: str, timeout: int = 30) -> dict:
        """Execute a project using firejail for sandboxing."""
        try:
            cmd = [
                'firejail', '--quiet', '--noprofile', '--net=none', '--private',
                '--noroot', '--nosound', '--no3d', '--nodvd', '--notv', '--nou2f',
                f'--bind={project_path},{project_path}',
                venv_python, entry_file
            ] + args_list
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=project_path)
            return _make_result(result.returncode == 0, result.stdout, result.stderr, result.returncode, 'firejail')
        
        except FileNotFoundError:
            return _make_result(False, '', 'firejail not found. Install with: sudo apt-get install firejail', -1, 'firejail')
        except subprocess.TimeoutExpired:
            return _make_result(False, '', f'Execution timeout after {timeout} seconds', -1, 'firejail')
        except Exception as e:
            return _make_result(False, '', f'Execution error: {str(e)}', -1, 'firejail')


class DockerMethod:
    """Docker container sandbox implementation."""
    
    name = 'docker'
    
    @staticmethod
    def is_available() -> bool:
        """Check if Docker is available and running."""
        if not shutil.which('docker'):
            return False

        try:
            subprocess.run(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            return False

        return True
    
    @staticmethod
    def execute(project_path: str, entry_file: str, args_list: list, venv_python: str, timeout: int = 30, image: str = 'python:3.12-slim') -> dict:
        """Execute a project in a Docker container."""
        try:
            # Mount project as /project in container
            entry_filename = os.path.basename(entry_file)
            venv_python_docker = os.path.join('/project/.venv', 'bin', 'python')
            entry_path_docker = os.path.join('/project', entry_filename)
            
            cmd = [
                'docker', 'run', '--rm', '--network=none', '--memory=512m', '--cpus=1',
                '--read-only', '--tmpfs', '/tmp:rw,noexec,nosuid',
                '-v', f'{project_path}:/project:ro',
                '-w', '/project',
                image,
                venv_python_docker, entry_path_docker
            ] + args_list
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return _make_result(result.returncode == 0, result.stdout, result.stderr, result.returncode, 'docker')
        
        except FileNotFoundError:
            return _make_result(False, '', 'docker not found. Install Docker Desktop or Docker Engine', -1, 'docker')
        except subprocess.TimeoutExpired:
            return _make_result(False, '', f'Execution timeout after {timeout} seconds', -1, 'docker')
        except Exception as e:
            return _make_result(False, '', f'Execution error: {str(e)}', -1, 'docker')


class BubblewrapMethod:
    """Bubblewrap sandbox implementation."""
    
    name = 'bubblewrap'
    
    @staticmethod
    def is_available() -> bool:
        """Check if bubblewrap is available."""
        return shutil.which('bwrap') is not None
    
    @staticmethod
    def execute(project_path: str, entry_file: str, args_list: list, venv_python: str, timeout: int = 30) -> dict:
        """Execute a project using bubblewrap."""
        try:
            cmd = [
                'bwrap',
                '--ro-bind', '/usr', '/usr',
                '--ro-bind', '/lib', '/lib',
                '--ro-bind', '/lib64', '/lib64',
                '--ro-bind', '/bin', '/bin',
                '--bind', project_path, project_path,
                '--proc', '/proc',
                '--dev', '/dev',
                '--unshare-all',
                '--die-with-parent',
                '--chdir', project_path,
                venv_python, entry_file
            ] + args_list
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=project_path)
            return _make_result(result.returncode == 0, result.stdout, result.stderr, result.returncode, 'bubblewrap')
        
        except FileNotFoundError:
            return _make_result(False, '', 'bubblewrap not found. Install with: sudo apt-get install bubblewrap', -1, 'bubblewrap')
        except subprocess.TimeoutExpired:
            return _make_result(False, '', f'Execution timeout after {timeout} seconds', -1, 'bubblewrap')
        except Exception as e:
            return _make_result(False, '', f'Execution error: {str(e)}', -1, 'bubblewrap')


class SubprocessMethod:
    """Subprocess execution without sandboxing."""
    
    name = 'subprocess'
    
    @staticmethod
    def is_available() -> bool:
        """Subprocess is always available."""
        return True
    
    @staticmethod
    def execute(project_path: str, entry_file: str, args_list: list, venv_python: str, timeout: int = 30) -> dict:
        """Execute a project using subprocess (no sandboxing)."""
        try:
            cmd = [venv_python, entry_file] + args_list
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=project_path)
            return _make_result(result.returncode == 0, result.stdout, result.stderr, result.returncode, 'subprocess')
        
        except subprocess.TimeoutExpired:
            return _make_result(False, '', f'Execution timeout after {timeout} seconds', -1, 'subprocess')
        except Exception as e:
            return _make_result(False, '', f'Execution error: {str(e)}', -1, 'subprocess')


# Registry of all available sandbox methods
SANDBOX_METHODS = {
    'firejail': FirejailMethod,
    'docker': DockerMethod,
    'bubblewrap': BubblewrapMethod,
    'subprocess': SubprocessMethod
}

# Methods for automatic sandbox selection, subprocess fallback is commented out for security reasons
# If you need subprocess fallback, specifically set method='subprocess' when calling execute_sandboxed_project
AUTO_METHODS = [
    FirejailMethod,
    DockerMethod,
    BubblewrapMethod,
#    SubprocessMethod
]


# Cache for availability checks
_sandbox_available_cache = {}

def sandbox_method_available(method: str) -> bool:
    """Check if a sandbox method is available on the system."""
    global _sandbox_available_cache
    
    if method in _sandbox_available_cache:
        return _sandbox_available_cache[method]
    
    if method not in SANDBOX_METHODS:
        return False
    
    result = SANDBOX_METHODS[method].is_available()
    _sandbox_available_cache[method] = result
    return result


# ==================== Project-based execution functions ====================

def _setup_project_venv(project_path: str) -> str:
    """Setup venv for a project and install requirements if present.
    
    Returns:
        Path to the venv directory
    """
    venv_path = os.path.join(project_path, '.venv')
    
    # Create venv if it doesn't exist
    if not os.path.exists(venv_path):
        print(f"Creating venv at: {venv_path}")
        subprocess.check_call([sys.executable, '-m', 'venv', venv_path], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Check for requirements.txt and install if present
    requirements_file = os.path.join(project_path, 'requirements.txt')
    if os.path.exists(requirements_file):
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        print(f"Installing packages from requirements.txt")
        subprocess.check_call([pip_path, 'install', '-r', requirements_file],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return venv_path


def execute_sandboxed(
    project: str,
    cmd_args: str,
    timeout: int = 30,
    method: str = 'auto'
) -> dict:
    """Execute a multi-file Python project with sandboxing.
    
    Args:
        project: Path to the project directory (e.g., './project' or '/tmp/myproject')
        cmd_args: Command with entry point and arguments (e.g., "main.py --verbose arg1")
        timeout: Execution timeout in seconds
        method: Sandbox method ('auto', 'firejail', 'docker', 'bubblewrap', 'subprocess')
    
    Returns:
        Dictionary with keys: success, stdout, stderr, exit_code, method
    
    Project structure expected:
        project/
        ├── main.py           # or other entry point specified in cmd_args
        ├── module1.py
        ├── module2.py
        ├── .venv/            # auto-created if doesn't exist
        └── requirements.txt  # optional, auto-installed if present
    """
    
    # Validate inputs
    if not project:
        return _make_result(False, '', 'project argument cannot be empty', -1, method)
    if not cmd_args:
        return _make_result(False, '', 'cmd_args argument cannot be empty', -1, method)
    
    # Common setup - do once for all methods
    project_path = os.path.abspath(project)
    if not os.path.exists(project_path):
        return _make_result(False, '', f'Project directory not found: {project_path}', -1, method)
    
    try:
        venv_path = _setup_project_venv(project_path)
        
        # Parse cmd_args
        parts = cmd_args.split()
        if not parts:
            return _make_result(False, '', 'cmd_args cannot be empty after parsing', -1, method)
        
        entry_point = parts[0]
        args_list = parts[1:]
        
        entry_file = os.path.join(project_path, entry_point)
        if not os.path.exists(entry_file):
            return _make_result(False, '', f'Entry point not found: {entry_file}', -1, method)
        
        venv_python = os.path.join(venv_path, 'bin', 'python')
    except Exception as e:
        return _make_result(False, '', f'Setup error: {str(e)}', -1, method)
    
    # Dispatch to specific method using registry
    if method in SANDBOX_METHODS:
        return SANDBOX_METHODS[method].execute(project_path, entry_file, args_list, venv_python, timeout)
    elif method == 'auto':
        # Try methods in order until one works
        for method_class in AUTO_METHODS:
            if not method_class.is_available():
                continue
            print(f"Trying sandbox method: {method_class.name}")
            
            result = method_class.execute(project_path, entry_file, args_list, venv_python, timeout)
            if 'not found' not in result['stderr']:
                return result
        
        # Return error if no sandbox methods are available
        return _make_result(False, '', 'No available sandbox methods found on the system.', -1, 'auto')
    else:
        return _make_result(False, '', f'Unknown sandbox method: {method}', -1, method)
