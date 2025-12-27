# Sandboxed Code Execution

The coding agent now supports sandboxed execution of generated code for improved security. There are two execution modes available:

1. **Single-file execution**: For simple scripts passed as code strings
2. **Project-based execution**: For multi-file Python projects with dependencies

## Execution Modes

### Single-File Execution (Original)

Use `execute_sandboxed()` for executing single Python files:

```python
from sandbox_execution import execute_sandboxed

result = execute_sandboxed(
    code="print('Hello World')",
    method='auto',
    timeout=30,
    args='arg1 arg2',  # optional command-line args
    venv_path='/path/to/venv',  # optional
    extra_packages=['requests', 'numpy']  # optional
)
```

### Project-Based Execution (New)

Use `execute_sandboxed_project()` for multi-file Python projects:

```python
from sandbox_execution import execute_sandboxed_project

result = execute_sandboxed_project(
    project='./my_project',  # path to project directory
    cmd_args='main.py --verbose arg1',  # entry point + arguments
    method='auto',
    timeout=30
)
```

**Project structure:**
```
./my_project/
├── main.py           # entry point
├── module1.py        # imported modules
├── module2.py
├── lib/
│   └── utils.py
├── .venv/            # auto-created if doesn't exist
└── requirements.txt  # auto-installed if present
```

**Features:**
- ✅ Automatic venv creation at `{project}/.venv`
- ✅ Auto-installs from `requirements.txt`
- ✅ Supports nested module imports
- ✅ Venv reused across multiple executions
- ✅ Full path isolation per sandbox method

## Sandbox Methods

### 1. Auto (Recommended)
```json
"sandbox_method": "auto"
```
Automatically tries sandboxing methods in order: `firejail` → `docker` → `bubblewrap`, but not `subprocess`

### 2. Firejail (Lightweight, Linux)
```json
"sandbox_method": "firejail"
```

**Installation:**
```bash
sudo apt-get install firejail
```

**Features:**
- ✅ No network access
- ✅ Limited filesystem access
- ✅ Private /tmp directory
- ✅ No privilege escalation
- ✅ Lightweight (no containers)

### 3. Docker (Full Isolation)
```json
"sandbox_method": "docker"
```

**Installation:**
```bash
# Install Docker Desktop or Docker Engine
# See: https://docs.docker.com/get-docker/
```

**Features:**
- ✅ Complete filesystem isolation
- ✅ No network access
- ✅ Resource limits (512MB RAM, 1 CPU)
- ✅ Read-only filesystem
- ✅ Works on Linux, macOS, Windows
- ⚠️ Slower startup (container overhead)

### 4. Bubblewrap (Linux Namespaces)
```json
"sandbox_method": "bubblewrap"
```

**Installation:**
```bash
sudo apt-get install bubblewrap
```

**Features:**
- ✅ Namespace isolation
- ✅ No network
- ✅ Limited filesystem access
- ✅ Very lightweight
- ⚠️ Linux only

### 5. Subprocess (Basic, No Sandbox)
```json
"sandbox_method": "subprocess"
```

**Features:**
- ✅ No dependencies
- ✅ Timeout protection
- ⚠️ **No security isolation**
- ⚠️ Only use for trusted code

## Configuration Examples

### High Security (C Interpreter)
```json
{
  "sandbox_method": "docker"
}
```

### Fast Iteration (Simple Tasks)
```json
{
  "sandbox_method": "firejail"
}
```

### Maximum Compatibility
```json
{
  "sandbox_method": "auto"
}
```

## Security Considerations

### What Sandboxing Protects Against
- ✅ File system access outside designated areas
- ✅ Network access
- ✅ Privilege escalation
- ✅ Resource exhaustion (with Docker)
- ✅ Malicious code execution

### What It Doesn't Protect Against
- ⚠️ CPU-intensive infinite loops (use timeout)
- ⚠️ Algorithmic complexity attacks
- ⚠️ Bugs in the Python interpreter itself

## Troubleshooting

### "firejail not found"
```bash
sudo apt-get install firejail
```

### "docker not found"
Install Docker Desktop or run:
```bash
curl -fsSL https://get.docker.com | sh
```

### "bwrap not found"
```bash
sudo apt-get install bubblewrap
```

### Sandbox fails but code is safe
Use `"sandbox_method": "subprocess"` for development/testing only.

## Performance Comparison

| Method | Startup Time | Security | Cross-Platform |
|--------|-------------|----------|----------------|
| firejail | ~50ms | High | Linux only |
| bubblewrap | ~30ms | High | Linux only |
| docker | ~500ms | Very High | Yes |
| subprocess | ~10ms | None | Yes |

## Recommendations

- **Development**: `auto` or `subprocess`
- **Production**: `firejail` (Linux) or `docker` (cross-platform)
- **Untrusted code**: `docker`
- **Performance critical**: `firejail` or `bubblewrap`
