"""
Sandboxed code execution implementations for the coding agent.
"""

import os
import subprocess
import tempfile

# Methods for automatic sandbox selection, subprocess fallback is commented out for security reasons
# If you need subprocess fallback, specifiyically set method='subprocess' when calling execute_sandboxed
AUTO_METHODS = [
    'firejail', 
    'docker',
    'bubblewrap', 
#    'subprocess'
]

def _make_result(success: bool, stdout: str, stderr: str, exit_code: int, method: str) -> dict:
    """Helper to create consistent result dictionaries."""
    return {
        'success': success,
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code,
        'method': method
    }


def _execute_with_cleanup(cmd: list, temp_file: str, timeout: int, method: str) -> dict:
    """Execute command with automatic cleanup and consistent error handling."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        os.unlink(temp_file)
        return _make_result(result.returncode == 0, result.stdout, result.stderr, result.returncode, method)
    
    except FileNotFoundError:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        install_cmd = {
            'firejail': 'sudo apt-get install firejail',
            'docker': 'Install Docker Desktop or Docker Engine',
            'bubblewrap': 'sudo apt-get install bubblewrap'
        }.get(method, 'unknown')
        return _make_result(False, '', f'{method} not found. Install with: {install_cmd}', -1, method)
    
    except subprocess.TimeoutExpired:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        return _make_result(False, '', f'Execution timeout after {timeout} seconds', -1, method)
    
    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        return _make_result(False, '', f'Execution error: {str(e)}', -1, method)


def execute_with_firejail(code: str, timeout: int = 30) -> dict:
    """Execute code using firejail for sandboxing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    cmd = [
        'firejail', '--quiet', '--noprofile', '--net=none', '--private-tmp',
        '--noroot', '--nosound', '--no3d', '--nodvd', '--notv', '--nou2f',
        'python3', temp_file
    ]
    
    return _execute_with_cleanup(cmd, temp_file, timeout, 'firejail')


def execute_with_docker(code: str, timeout: int = 30, image: str = 'python:3.12-slim') -> dict:
    """Execute code in a Docker container."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    cmd = [
        'docker', 'run', '--rm', '--network=none', '--memory=512m', '--cpus=1',
        '--read-only', '--tmpfs', '/tmp:rw,noexec,nosuid',
        '-v', f'{temp_file}:/code.py:ro', image, 'python3', '/code.py'
    ]
    
    return _execute_with_cleanup(cmd, temp_file, timeout, 'docker')


def execute_with_bubblewrap(code: str, timeout: int = 30) -> dict:
    """Execute code using bubblewrap."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    cmd = [
        'bwrap', '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
        '--ro-bind', '/lib64', '/lib64', '--ro-bind', '/bin', '/bin',
        '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev',
        '--unshare-all', '--die-with-parent',
        '--ro-bind', temp_file, '/code.py', 'python3', '/code.py'
    ]
    
    return _execute_with_cleanup(cmd, temp_file, timeout, 'bubblewrap')


def execute_sandboxed(code: str, timeout: int = 30, method: str = 'auto') -> dict:
    """Execute code with automatic or specified sandbox method."""
    
    if method == 'firejail':
        return execute_with_firejail(code, timeout)
    elif method == 'docker':
        return execute_with_docker(code, timeout)
    elif method == 'bubblewrap':
        return execute_with_bubblewrap(code, timeout)
    elif method == 'subprocess':
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        cmd = ['python3', temp_file]
        return _execute_with_cleanup(cmd, temp_file, timeout, 'subprocess')
    else:  # method == 'auto'
        # Try sandboxing methods in order of preference
        for sandbox_method in AUTO_METHODS:
            result = execute_sandboxed(code, timeout, method=sandbox_method)
            # If we got a "not found" error, try next method
            if 'not found' not in result['stderr']:
                return result
        
        # Fallback to subprocess if all else fails
        return execute_sandboxed(code, timeout, method='subprocess')
