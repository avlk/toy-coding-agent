from google.genai import types
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

def create_subagent_coding(model_config: ModelConfig, mcp: MCPInstance, token_tracker: TokenUsageTracker, instruction, **kwargs) -> SubAgentGoogle:
    
    # planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(thinking_budget=20000))
    # planner = PlanReActPlanner()
    planner=None
    # To use GoogleAIAgent: uncomment import above and this will automatically use SubAgentGoogle
    subagent = SubAgentGoogle(
        name="coding_subagent",
        model=model_config.name, 
        token_tracker=token_tracker,
        system_instruction=instruction, 
        mcp_toolset=mcp.get_toolset(),
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

async def test_coding_agent(model_name: str, test_name: str, script_name: str, nrounds: int):
    # Filter out deprecation warnings from google-adk since they use their own deprecated APIs
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    system_instruction = load_file(f"scripts/subagents/coding/{script_name}.md")
    use_case = load_file(f"test_sets/{test_name}/use case.md")
    goals = load_file(f"test_sets/{test_name}/goals.md")
    feedback = load_file(f"test_sets/{test_name}/iteration goal.md")

    token_tracker = TokenUsageTracker()
    model_config = find_model_config(model_name)
    request_throttler = get_throttler(model_config.rpm, model_config.tpm, model=model_config.name) 

    mcp = MCPInstance(project_path=f"solutions/{test_name}")
    if not await mcp.start():
        print("Failed to start MCP server")
        return

    success_rounds = []

    try:
        subagent = create_subagent_coding(model_config, mcp, token_tracker, system_instruction, rate_limiter=request_throttler)
        subagent.set_debug(True)
        subagent.set_progress_indication(False)

        for round_num in range(nrounds):            
            print("\n" + "="*80)
            print(f"\n🔄 Starting test round {round_num+1} of {nrounds}")
            print("\n" + "="*80)

            prepare_test_files(test_name)
            parts = [("Use Case", use_case), ("Goals", goals), ("Review Feedback", feedback)]
            await subagent.query(query="Implement changes addressing feedback items.", parts=parts)

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
    args = parser.parse_args()

    try:
        # Create persistent event loop for clean async handling
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(test_coding_agent(args.model, args.test, args.script, args.rounds))
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