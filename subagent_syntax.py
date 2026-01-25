from google.genai import types
from subagent_google import SubAgentGoogle
from google.adk.planners import PlanReActPlanner, BuiltInPlanner
from mcp_instance import MCPInstance
from token_tracker import TokenUsageTracker

system_instruction = """
You are a top grade syntax fixing agent. Your task is to fix any syntax errors in the provided Python code.
You don't need to understand the full program logic, just fix the syntax issues.

You have to use MCP tools to accomplish your task:
- first use `run_ruff_check()` to identify errors. If there are errors, the response will contain an `issues` list with file paths and line numbers.
- then analyze the errors and fix them using the following approach:
- summarize the errors, group them by file and then group errors that have close line numbers together
- for each file with errors, read the relevant lines using `get_line_range` to understand the context of the error. 
  Make sure to read a 10 lines before and 10 lines after the error lines to get full context.
- then imagine the most possible root cause for each group of errors, since many errors at the same line or adjacent lines are likely introduced by just one error.
- fix this root cause using TARGETED edits, such as `fuzzy_replace_in_file` or `multiline_replace_in_file` for small fixes.
- only if the error is widespread (like wrong indentation across many lines), use bulk refactoring using `replace_in_files` with regex patterns. 
- For targeted edits, use `fuzzy_replace_in_file(file_path, search_lines, replace_lines, around_line)` and `replace_in_files(pattern, replacement, is_regex, file_pattern)`
- DO NOT use `fuzzy_replace_in_file` multiple times in the same round for the same file - this will lead to errors as `around_line` will be offset.
- If `fuzzy_replace_in_file` fails multiple times, try to achieve the same with `replace_in_files` and regex patterns.
- For bulk refactoring (like renaming variables), use `replace_in_files(pattern, replacement, is_regex, file_pattern)`
- After making edits, use `run_ruff_check()` again to verify fixes.
- When you call `run_ruff_check()`, check the response. If it contains 'success': True, this means there are no syntax errors.
- When there are no syntax errors, you MUST end your work and return your summary.

Your tools:
- `list_files()` - List files in the project.
- `get_line_range(file_path, start, end)` - Read specific lines of the file
- `search_files(pattern)` - Case-sensitive search for a text match across project files. Returns a list of matching strings and matching file metadata.
- `find_python_definition(name)` - Find Python definition of a class, method or function. Returns the lines with declaration and definition (all lines), file metadata, line numbers of the definition. 
- `replace_in_files(pattern, replacement, is_regex=False)` - Search and replace a string pattern across all matching files in the project. Returns dict mapping file paths to number of replacements made. Only saves files where replacements occurred.
- `replace_in_files(pattern, replacement, is_regex=False, file_pattern)` - Extended `replace_in_files` call, where `file_pattern` filters which files to process (e.g., "*.py").
- `replace_in_files(pattern, replacement, is_regex=True)` - Extended `replace_in_files` call, where pattern is treated as regex and replacement may have backreferences.
- `replace_in_files(pattern, replacement, is_regex=True)` - Extended `replace_in_files` call, pattern is treated as regex and replacement may have backreferences, and `file_pattern` filters which files to process (e.g., "*.py").
- `fuzzy_replace_in_file(file_path, search_lines, replace_lines, around_line)` - Forgiving tool for multiline replacement in files. Will find a close match for `search_lines` (list of strings) around line `around_line`, and replace the match with `replace_lines`. Use it for small edits, such as syntax error fixes.
- `multiline_replace_in_file(file_path, search_lines, replace_lines)` - Search and replace a matching line sequence with another line sequence in a specific file. Returns number of replacements made.
- `multiline_replace_in_file(file_path, search_lines, replace_lines, only_around_line)` - Extended multiline replacement. If `only_around_line` is specified (1-indexed line number), only replaces the match closest to that line. Use it to only make one replacement around specific location.
- `run_ruff_check(file_pattern, fix)` - Extended Ruff check. `file_pattern` filters files to check (default: "**/*.py"). If `fix=True`, automatically fixes fixable issues (WARNING: modifies files). Returns dict with 'success' status, and if 'success' is false, 'error' message, and 'issues' list.

## Response Format
IMPORTANT: After completing all your work, you MUST provide a final summary in this format:

1. **What I completed**: Describe what you implemented (fixes made, files changed, etc.)
2. **What could not be fixed**: Brief summary of what could not be fixed (if any)

Always end your work with this summary format. Do not end without providing this summary.
"""

allowed_tools = [
        "list_files",
        "get_line_range",
        "search_files",
        "find_python_definition",
        "replace_in_files",
        "fuzzy_replace_in_file",
        "multiline_replace_in_file",
        "run_ruff_check"
    ]

model="gemini-2.5-flash"

def create_subagent_syntax(mcp: MCPInstance, token_tracker: TokenUsageTracker) -> SubAgentGoogle:

    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(thinking_budget=5000))

    # To use GoogleAIAgent: uncomment import above and this will automatically use SubAgentGoogle
    subagent = SubAgentGoogle(
        name="syntax_subagent",
        model=model, 
        token_tracker=token_tracker,
        system_instruction=system_instruction, 
        mcp_toolset=mcp.get_toolset(allowed_tools),
        planner=planner
    )
    return subagent

# Test case
import os
import shutil
import asyncio
import time
from token_tracker import TokenUsageTracker
from mcp_instance import MCPInstance
from coding_agent import ProjectFolder
import warnings

def prepare_test_files(test_name: str):
    # Copy test files to solutions/{test_name}
    if os.path.exists(f"solutions/{test_name}"):
        shutil.rmtree(f"solutions/{test_name}")
    shutil.copytree(f"test_sets/{test_name}", f"solutions/{test_name}")

async def test_streaming_agent():
    # Filter out deprecation warnings from google-adk since they use their own deprecated APIs
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    # Copy test files to solutions/test_streaming_agent
    test_name = "test_streaming_agent"
    token_tracker = TokenUsageTracker()

    mcp = MCPInstance(project_path=f"solutions/{test_name}")
    if not await mcp.start():
        print("Failed to start MCP server")
        return

    nrounds = 5
    success_rounds = []
        
    try:
        subagent = create_subagent_syntax(mcp, token_tracker)
        subagent.set_debug(True)
        subagent.set_progress_indication(False)

        for round_num in range(nrounds):            
            prepare_test_files(test_name)

            await subagent.query(query="Fix all syntax errors in the project code.")

            # run ruff check to verify no syntax errors remain using MCPInstance
            ruff_result = await mcp.execute_function_call('run_ruff_check', file_pattern="**/*.py", fix=False)
            print(f"\n🔍 Ruff check result: {ruff_result}")
            if 'structuredContent' in ruff_result:
                res = ruff_result['structuredContent']
                if res.get('success', False):
                    print(f"\n✅ All syntax errors fixed!")
                    success_rounds.append(round_num)
                else:
                    print(f"\n🔄 Syntax errors still remain") 
                    print(f"Issues: {res.get('issues', [])}")      
            else:
                print(f"\n❗ Unexpected Ruff result format")
        print("="*80)
        print(f"\nTest completed: {len(success_rounds)} out of {nrounds} rounds successful")
        print(f"Successful rounds: {success_rounds}")
        token_tracker.print_summary()
    finally:
        mcp.stop()

if __name__ == "__main__":
    try:
        # Create persistent event loop for clean async handling
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(test_streaming_agent())
    finally:
        # Cleanup pending tasks before closing loop
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                # Cancel all pending tasks
                for task in pending:
                    task.cancel()
                
                # Wait for cancellation to complete
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        except Exception:
            pass  # Ignore cleanup errors
        finally:
            loop.close()