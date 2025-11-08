# Sandboxed Code Execution

The coding agent now supports sandboxed execution of generated code for improved security.

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
  "coder_model": "gemini-2.5-pro",
  "reviewer_model": "gemini-2.5-pro",
  "utility_model": "gemini-2.5-flash-lite",
  "max_rounds": 25,
  "basename": "interp",
  "sandbox_method": "docker"
}
```

### Fast Iteration (Simple Tasks)
```json
{
  "coder_model": "gemini-2.5-flash",
  "reviewer_model": "gemini-2.5-flash",
  "utility_model": "gemini-2.5-flash-lite",
  "max_rounds": 10,
  "basename": "quicktest",
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
