"""
Sandboxed code execution implementations for the coding agent.
"""

import os
import subprocess
import tempfile

# Methods for automatic sandbox selection, subprocess fallback is commented out for security reasons
# If you need subprocess fallback, specifically set method='subprocess' when calling execute_sandboxed
AUTO_METHODS = [
    'firejail', 
    'docker',
    'bubblewrap', 
#    'subprocess'
]

def _make_result(success: bool, stdout: str, stderr: str, exit_code: int, method: str) -> dict:
    """Helper function to create consistent result dictionaries."""
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


def execute_with_firejail(code: str, timeout: int = 30, args: str = '', venv_path: str = None) -> dict:
    """Execute code using firejail for sandboxing. Supports venv if venv_path is given."""
    import os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name

    cmd = [
        'firejail', '--quiet', '--noprofile', '--net=none', '--private-tmp',
        '--noroot', '--nosound', '--no3d', '--nodvd', '--notv', '--nou2f'
    ]
    if venv_path:
        venv_python = os.path.join(venv_path, 'bin', 'python')
        # Bind-mount the venv into the sandbox at the same path
        cmd.extend([
            f'--bind={venv_path},{venv_path}', 
            venv_python, temp_file
        ])
    else:
        cmd.extend([
            'python3', temp_file
        ])
    # Add command-line arguments if provided
    if args:
        cmd.extend(args.split())

    return _execute_with_cleanup(cmd, temp_file, timeout, 'firejail')


def execute_with_docker(code: str, timeout: int = 30, image: str = 'python:3.12-slim', args: str = '', venv_path: str = None) -> dict:
    """Execute code in a Docker container. Supports venv if venv_path is given."""
    import os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name

    mounts = [f'-v', f'{temp_file}:/code.py:ro']
    if venv_path:
        venv_python = os.path.join(venv_path, 'bin', 'python')
        mounts += ['-v', f'{venv_path}:{venv_path}:ro']
        python_cmd = [venv_python, '/code.py']
    else:
        python_cmd = ['python3', '/code.py']

    cmd = [
        'docker', 'run', '--rm', '--network=none', '--memory=512m', '--cpus=1',
        '--read-only', '--tmpfs', '/tmp:rw,noexec,nosuid',
    ] + mounts + [image] + python_cmd

    # Add command-line arguments if provided
    if args:
        cmd.extend(args.split())

    return _execute_with_cleanup(cmd, temp_file, timeout, 'docker')


def execute_with_bubblewrap(code: str, timeout: int = 30, args: str = '', venv_path: str = None) -> dict:
    """Execute code using bubblewrap. Supports venv if venv_path is given."""
    import os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name

    base_cmd = [
        'bwrap', '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
        '--ro-bind', '/lib64', '/lib64', '--ro-bind', '/bin', '/bin',
        '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev',
        '--unshare-all', '--die-with-parent',
        '--ro-bind', temp_file, '/code.py'
    ]

    if venv_path:
        venv_python = os.path.join(venv_path, 'bin', 'python')
        base_cmd += ['--ro-bind', venv_path, venv_path]
        python_cmd = [venv_python, '/code.py']
    else:
        python_cmd = ['python3', '/code.py']

    cmd = base_cmd + python_cmd

    # Add command-line arguments if provided
    if args:
        cmd.extend(args.split())

    return _execute_with_cleanup(cmd, temp_file, timeout, 'bubblewrap')


def execute_sandboxed(
    code: str,
    timeout: int = 30,
    method: str = 'auto',
    args: str = '',
    venv_path: str = None,
    extra_packages: list = None
) -> dict:
    """Execute code with automatic or specified sandbox method.
    
    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds
        method: Sandbox method ('auto', 'firejail', 'docker', 'bubblewrap', 'subprocess')
        args: Command-line arguments to pass to the Python script (space-separated string)
        venv_path: Path to a Python virtual environment to use (optional)
        extra_packages: List of extra Python packages to install in the venv (optional)
    """

    def ensure_venv_and_packages(venv_path, extra_packages):
        import sys
        import subprocess
        import os
        # Create venv if it doesn't exist
        if not os.path.exists(venv_path):
            print("Creating venv at:", venv_path)
            subprocess.check_call([sys.executable, '-m', 'venv', venv_path])
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        print("Pip path:", pip_path)
        if extra_packages:
            print("Installing extra packages:", extra_packages)
            subprocess.check_call([pip_path, 'install'] + list(extra_packages))
        python_path = os.path.join(venv_path, 'bin', 'python')
        print("Using python at:", python_path)
        return python_path

    # If venv_path is specified, ensure it and extra packages are set up
    if venv_path:
        try:
            ensure_venv_and_packages(venv_path, extra_packages)
        except Exception as e:
            return _make_result(False, '', f'Venv setup error: {str(e)}', -1, 'venv')

    # Dispatch to the appropriate sandbox method
    if method == 'firejail':
        return execute_with_firejail(code, timeout, args, venv_path=venv_path)
    elif method == 'docker':
        return execute_with_docker(code, timeout, args=args, venv_path=venv_path)
    elif method == 'bubblewrap':
        return execute_with_bubblewrap(code, timeout, args=args, venv_path=venv_path)
    elif method == 'subprocess':
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        if venv_path:
            python_path = os.path.join(venv_path, 'bin', 'python')
            cmd = [python_path, temp_file]
        else:
            cmd = ['python3', temp_file]
        if args:
            cmd.extend(args.split())
        return _execute_with_cleanup(cmd, temp_file, timeout, 'subprocess')
    else:  # method == 'auto'
        for sandbox_method in AUTO_METHODS:
            result = execute_sandboxed(code, timeout, method=sandbox_method, args=args, venv_path=venv_path, extra_packages=extra_packages)
            if 'not found' not in result['stderr']:
                return result
        return execute_sandboxed(code, timeout, method='subprocess', args=args, venv_path=venv_path, extra_packages=extra_packages)
