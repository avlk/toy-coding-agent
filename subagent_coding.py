from google.genai import types
import mcp
from subagent_google import SubAgentGoogle
from google.adk.planners import PlanReActPlanner, BuiltInPlanner
from mcp_instance import MCPInstance
from token_tracker import TokenUsageTracker
from utils import load_file
from throttler import get_throttler

class ModelConfig:
    def __init__(self, name: str, rpm: int, tpm: int):
        self.name = name
        self.rpm = rpm
        self.tpm = tpm

# Select model configuration
model_configs = [ModelConfig("gemini-2.5-flash-lite", rpm=850, tpm=3_000_000),
                 ModelConfig("gemini-2.5-flash", rpm=450, tpm=450_000),
                 ModelConfig("gemini-3-flash-preview", rpm=850, tpm=850_000)]

def find_model_config(model_name: str) -> ModelConfig:
    for config in model_configs:
        if config.name == model_name:
            return config
    raise ValueError(f"Model configuration for {model_name} not found")

def create_subagent_coding(model_config: ModelConfig, mcp: MCPInstance, token_tracker: TokenUsageTracker, instruction, checklist: bool, **kwargs) -> SubAgentGoogle:
    allow_tools = ["create_snapshot", "restore_snapshot", "list_snapshots",
                   "list_files", "create_file", "remove_file",
                   "load_file", "get_line_range",
                   "search_files", "find_python_definition", 
                   "execute_project", "run_ruff_check",
                   "multiline_replace_in_file", "replace_in_files"
                   ]
    if checklist:
        allow_tools.extend(["checklist_read", "checklist_complete"])

    agent_name = "coding_subagent"
    if checklist:
        agent_name = "coding_subagent_cl"

    # planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(thinking_budget=20000))
    # planner = PlanReActPlanner()
    planner=None
    # To use GoogleAIAgent: uncomment import above and this will automatically use SubAgentGoogle
    subagent = SubAgentGoogle(
        name=agent_name,
        model=model_config.name, 
        token_tracker=token_tracker,
        system_instruction=instruction, 
        mcp_toolset=mcp.get_toolset(allowed_tools=allow_tools),
        planner=planner, **kwargs
    )
    return subagent



# Test case
import os
import shutil
import asyncio
import argparse
from token_tracker import TokenUsageTracker
from mcp_instance import MCPInstance
import warnings

def prepare_test_files(test_name: str):
    # Copy test files to solutions/{test_name}
    if os.path.exists(f"solutions/{test_name}"):
        shutil.rmtree(f"solutions/{test_name}/")
    shutil.copytree(f"test_sets/{test_name}/test", f"solutions/{test_name}/current/code")
    # copy review checklist to solutions/{test_name}/current/checklists folder
    os.makedirs(f"solutions/{test_name}/current/checklists", exist_ok=True)
    shutil.copy(f"test_sets/{test_name}/review.json", f"solutions/{test_name}/current/checklists/review.json")


    
async def test_coding_agent(model_name: str, test_name: str, script_name: str, checklist: bool, nrounds: int):
    # Filter out deprecation warnings from google-adk since they use their own deprecated APIs
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    if checklist:
        system_instruction = load_file(f"scripts/subagents/coding-checklist/{script_name}.md")
    else:
        system_instruction = load_file(f"scripts/subagents/coding/{script_name}.md")
    use_case = load_file(f"test_sets/{test_name}/use case.md")
    goals = load_file(f"test_sets/{test_name}/goals.md")
    feedback = load_file(f"test_sets/{test_name}/iteration goal.md")

    token_tracker = TokenUsageTracker()
    model_config = find_model_config(model_name)
    request_throttler = get_throttler(model_config.rpm, model_config.tpm, model=model_config.name, token_tracker=token_tracker) 

    mcp = MCPInstance(project_path=f"solutions/{test_name}")
    if not await mcp.start():
        print("Failed to start MCP server")
        return

    success_rounds = []

    try:
        subagent = create_subagent_coding(model_config, mcp, token_tracker, system_instruction, checklist, rate_limiter=request_throttler)
        subagent.set_debug(True)
        subagent.set_progress_indication(False)

        for round_num in range(nrounds):            
            print("\n" + "="*80)
            print(f"\n🔄 Starting test round {round_num+1} of {nrounds}")
            print("\n" + "="*80)

            prepare_test_files(test_name)

            # Set iteration and agent role for checklist metadata
            await mcp.execute_function_call('_set_iteration_info', current_iteration=2, current_role="coder")
            await mcp.execute_function_call('_set_actionable_checklist', checklist_name="review")
            # Prepare prompt
            parts = [("Use Case", use_case), ("Goals", goals), ("Review Feedback", feedback)]
            await subagent.query(query="Implement changes addressing feedback items.", parts=parts, stopword="###STOPWORD###", n_iterations=10)

            # run ruff check to verify no syntax errors remain using MCPInstance
            print(f"\n🔍 Executing project to verify...")
            result = await mcp.execute_function_call('execute_project', cmd_args="main.py --test")
            print(result)
            if 'structuredContent' in result:
                res = result['structuredContent']
                if res.get('success', False):
                    print(f"\n✅ All tests pass!")
                    success_rounds.append(round_num)
                else:
                    print(f"\n🔄 Errors still remain") 
            else:
                print(f"\n❗ Unexpected result format")
        print("="*80)
        print(f"\nTest completed: {len(success_rounds)} out of {nrounds} rounds successful")
        print(f"Successful rounds: {success_rounds}")
        token_tracker.print_summary()
    finally:
        mcp.stop()

if __name__ == "__main__":

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Coding subagent test")
    parser.add_argument("--model", help="Model name", type=str, default="gemini-2.5-flash")
    parser.add_argument("--test", help="Test set", type=str, default="test_coding_agent")
    parser.add_argument("--script", help="System instruction variant", type=str, default="full")
    parser.add_argument("--rounds", type=int, default=1, help="Number of coding rounds to execute (default: 1)")
    parser.add_argument("--checklist", action="store_true", help="Enable checklists for subagent")
    args = parser.parse_args()

    try:
        # Create persistent event loop for clean async handling
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(test_coding_agent(args.model, args.test, args.script, args.checklist, args.rounds))
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