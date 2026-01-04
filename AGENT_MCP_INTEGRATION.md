# Agent-Based Code Generation with MCP Integration

## Overview

The `coding_agent.py` system uses Google ADK's `LlmAgent` with MCP (Model Context Protocol) integration to provide autonomous code generation with direct file system access.

## Architecture

### 1. **Agentic Chat-Based Workflow**
- Uses `google.adk.agents.LlmAgent` for true agentic behavior
- Agent is created **once** before all iterations and maintains conversation state
- Agent operates in **chat mode** - `agent.chat()` preserves context across iterations
- No need to pass previous code in prompts - agent has full conversation history

### 2. **MCP Server Integration**
- Agent spawns and manages MCP server subprocess automatically via `StdioConnectionParams`
- MCP server provides access to project directory: `solutions/{task_name}/`
- Agent manages server lifecycle - no manual cleanup needed
- Connection details:
  ```python
  MCPToolset(
      connection_params=StdioConnectionParams(
          server_params=StdioServerParameters(
              command=sys.executable,
              args=[mcp_script, project_path]
          )
      )
  )
  ```

### 3. **File-Based Code Management**
- Agent uses `create_file` tool to save code directly to `code.py`
- Agent uses `load_file` tool to read existing code when needed
- Agent uses `apply_patch` for incremental changes
- **Code function reads from file** instead of parsing response text
- No code blocks in agent responses - just explanations

### 4. **MCP Tools Available**
The agent has autonomous access to:
- `list_files(pattern)` - Explore project structure
- `load_file(file_path)` - Read any file
- `create_file(file_path, content, overwrite)` - Save/update files
- `remove_file(file_path)` - Delete files
- `get_line_range(file_path, start, end)` - Read specific lines
- `search_files(pattern, is_regex, case_sensitive)` - Search codebase
- `find_python_definition(name, def_type)` - Find Python symbols
- `apply_patch(patch_content, fuzziness)` - Apply diffs
- `execute_project(cmd_args, timeout)` - Test code in sandbox

## Key Benefits

1. **True Autonomy**: Agent decides when and how to use tools
2. **Conversational Context**: Full history maintained across iterations
3. **Direct File Operations**: No parsing of code blocks from responses
4. **Efficient**: Agent created once, MCP server managed automatically
5. **Safer**: Agent can read code before modifying, test changes

## Workflow Example

**Iteration 1:**
```
User → Agent: "Create a Python calculator"
Agent: creates code.py using create_file tool
Agent: tests with execute_project
Agent: responds with explanation
```

**Iteration 2:**
```
User → Agent: "Add division, fix the error"
Agent: reads code.py using load_file
Agent: updates code.py using create_file or apply_patch
Agent: tests with execute_project
Agent: responds with what was fixed
```

## Implementation Details

### Agent Creation (Once)
```python
agent = LlmAgent(
    model=task_config["coder_model"],
    name='code_generator',
    instruction='You are an expert Python code generator.',
    tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=sys.executable,
                    args=[mcp_script, project_path]
                )
            )
        )
    ]
)
```

### Each Iteration
```python
# Build prompt with context
response = agent.chat(prompt_text)  # Agent maintains history

# Read code from file (agent saved it)
code_file = os.path.join(project_path, "code.py")
with open(code_file, 'r') as f:
    code_content = f.read()
context.current.code = to_lines(code_content)
```

### Prompt Structure
- **System instruction** (cached, unchanged): Role, constraints, tools explanation
- **User messages** (per iteration): Feedback, execution results, TODO items
- **No code in prompts**: Agent has conversation history and MCP access

## Usage

Run as before - the agent integration is transparent:

```bash
python coding_agent.py <task_name>
```

The agent will:
- Create once at start
- Use MCP tools throughout all iterations
- Maintain conversation context
- Automatically clean up when done

## Advantages Over Previous Approach

| Aspect | Old (generate_content) | New (LlmAgent + MCP) |
|--------|------------------------|----------------------|
| **State** | Stateless | Stateful conversation |
| **Code Handling** | Parse from response | Direct file operations |
| **Context** | Re-send each time | Maintained automatically |
| **Tool Usage** | Single-shot | Multi-turn autonomous |
| **MCP Server** | Manual management | Automatic lifecycle |
| **Agent Creation** | Per iteration | Once per session |

## Troubleshooting

**Agent not using tools:**
- Check MCP server path is correct
- Verify project directory exists
- Review agent responses for tool call patterns

**Code not found:**
- Agent should use `create_file(file_path="code.py", ...)` 
- Check if agent is outputting code instead of using tools
- Review prompts - ensure they instruct agent to use tools

**MCP server issues:**
- Check stderr from mcp_server.py subprocess
- Verify fastmcp is installed: `pip install fastmcp`
- Test MCP server standalone: `python mcp_server.py /tmp/test`

**Conversation state issues:**
- Agent maintains full history automatically
- If needed, conversation can be reset by creating new agent
- Check token limits if very long conversations

## Future Enhancements

- Multi-file projects (agent can already manage multiple files)
- Incremental testing (agent tests after each change)
- Interactive debugging (agent can read execution results and fix)
- Code analysis (agent can search and analyze patterns)
- Documentation generation (agent can read and document code)
