# Copyright (c) 2025 Andrey Volkov

# This work is a derivative work based on the original by Mahtab Syed.
# Original author copyright notice:
# MIT License
# Copyright (c) 2025 Mahtab Syed
# https://www.linkedin.com/in/mahtabsyed/

import os
import random
import re
import sys
import json
import time
import subprocess
import tempfile
from pathlib import Path
from google import genai
from patch import patch_code, is_unified_diff
from md_parser import find_code_blocks
from sandbox_execution import execute_sandboxed
from utils import *

# Initialize Gemini LLM
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set")

default_llm_model = "gemini-2.5-pro"
print(f"📡 Initializing Gemini LLM ({default_llm_model})...")
llm = genai.Client(api_key=api_key)
llm_config = genai.types.GenerateContentConfig(
    temperature=0.3,
    tools=[genai.types.Tool(code_execution=genai.types.ToolCodeExecution)]
)

llm_config_coder = genai.types.GenerateContentConfig(
    temperature=0.3,
    tools=[genai.types.Tool(code_execution=genai.types.ToolCodeExecution)],
)

llm_config_goals_check = genai.types.GenerateContentConfig(
    temperature=0.3,
    responseMimeType="text/x.enum",
    responseSchema={
        "type": "string",
        "enum": ["Yes", "No"],
    },
)

llm_config_refine_task = genai.types.GenerateContentConfig(
    temperature=0.1,
    responseMimeType="application/json",
    responseSchema={
        "type": "object",
        "properties": {
            "refined_use_case": {
                "type": "string",
                "description": "The refined use case text"
            },
            "refined_goals": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of refined goals as separate strings"
            }
        },
        "required": ["refined_use_case", "refined_goals"]
    },
)

# Default configuration structure
DEFAULT_TASK_CONFIG = {
    "coder_model": "gemini-2.5-pro",
    "reviewer_model": "gemini-2.5-pro", 
    "utility_model": "gemini-2.5-flash-lite",
    "max_rounds": 25,
    "basename": "code",
    "sandbox_method": "auto",  # Options: auto, firejail, docker, bubblewrap, subprocess
    "commandline_args": ""
}

def llm_query(query, config=llm_config, model=default_llm_model):
    # mark start time
    start_time = time.monotonic()
    response = llm.models.generate_content(
        model=model, contents=query, config=config
    )
    end_time = time.monotonic()
    # Calculate generation time in seconds
    generation_time = end_time - start_time
    text = response.text

    return {"text": text, "full": response, "usage": response.usage_metadata, "response_time": generation_time}

def print_usage_info(metadata, time):
    print("Token Usage Info: total {}, cache {}, candidates {}, prompt {}, thoughts {}, tool_use {}".format(
        metadata.total_token_count,
        metadata.cached_content_token_count,
        metadata.candidates_token_count,
        metadata.prompt_token_count,
        metadata.thoughts_token_count,
        metadata.tool_use_prompt_token_count
    ))
    print(f"Time taken for LLM call: {time:.1f} seconds")

# --- Agent-Specific Functions ---

def load_task_config(config_name: str) -> dict:
    """Load configuration from tasks/{config_name}/config.json"""
    config_path = Path(f"tasks/{config_name}/config.json")
    
    if not config_path.exists():
        print(f"⚠️  Config file not found: {config_path}")
        print("🔄 Using default configuration")
        return DEFAULT_TASK_CONFIG.copy()
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Start with defaults and update with loaded values
        final_config = DEFAULT_TASK_CONFIG.copy()
        final_config.update(config)
        
        print(f"📋 Loaded config: coder={final_config['coder_model']}, reviewer={final_config['reviewer_model']}, utility={final_config['utility_model']}, max_rounds={final_config['max_rounds']}")
        return final_config
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Error loading config from {config_path}: {e}")
        print("🔄 Using default configuration")
        return DEFAULT_TASK_CONFIG.copy()

def generate_prompt(use_case: str, goals: str, previous_code = None, feedback: str = None) -> str:
    """
    Generate prompt for code generation.
    
    Args:
        use_case: Use case description (string)
        goals: Goals description (string)
        previous_code: Previous code (can be string or list, will be converted to string)
        feedback: Feedback text (string)
    
    Returns:
        Formatted prompt string
    """
    print("📝 Constructing prompt for code generation...")

    if previous_code:
        print("🔄 Adding previous code to the prompt for refinement.")
        script_path = "scripts/coder fix.md"
    else:
        script_path = "scripts/coder create.md"

    script = load_file(script_path)
    
    # Convert previous_code to string if it's a list
    previous_code_str = to_string(previous_code) if previous_code else None
    
    base_prompt = script.format_map({
        "use_case": use_case,
        "goals": goals,
        "previous_code": previous_code_str,
        "feedback": feedback
    })

    return base_prompt

def get_code_feedback(use_case: str, code: str, goals: str, code_output: str, reviewer_model: str = default_llm_model) -> str:
    print("🔍 Evaluating code against the goals...")

    script_path = "scripts/reviewer.md"
    script = load_file(script_path)
    feedback_prompt = script.format_map({
        "use_case": use_case,
        "goals": goals,
        "code": code,
        "code_output": code_output
    })
    return llm_query(feedback_prompt, model=reviewer_model)["text"]

def goals_met(feedback_text: str, goals: str, utility_model: str = default_llm_model) -> bool:
    """
    Uses the LLM to evaluate whether the goals have been met based on the feedback text.
    Returns True or False (parsed from LLM output).
    """
    script_path = "scripts/goals check.md"
    script = load_file(script_path)
    review_prompt = script.format_map({
        "goals": goals,
        "feedback_text": feedback_text
    })  
    response = llm_query(review_prompt, config=llm_config_goals_check, model=utility_model)["text"].strip().lower()
    print(f"🎯 Goals met evaluation: {response}")
    return response == "yes"

def add_comment_header(code, use_case, task_config: dict) -> list:
    """
    Add comment header to code.
    
    Args:
        code: Either a string or list of lines
        use_case: Either a string or list of lines describing the use case
        task_config: Dictionary with task configuration
    
    Returns:
        List of lines with comment header prepended
    """
    comment = []
    comment.append(f"# This Python program implements the following use case:")
    use_case_lines = to_lines(use_case)
    for line in use_case_lines:
        comment.append(f"# {line.strip()}")
    comment.append(f"# Generated by AI Code Generation Agent")
    comment.append(f"# Models used: coder={task_config['coder_model']}, reviewer={task_config['reviewer_model']}, utility={task_config['utility_model']}")
    comment.append(f"# Max rounds: {task_config['max_rounds']}")
    comment.append("")  # Empty line separator
    
    code_lines = to_lines(code)
    return comment + code_lines

def execute_code_locally(code: str, timeout: int = 30, sandbox_method: str = 'auto', args: str = '') -> dict:
    """
    Execute Python code locally in a sandbox and capture output.
    Returns dict with 'success', 'stdout', 'stderr', 'exit_code'
    
    Delegates to sandbox_execution module which supports:
    - firejail (lightweight Linux sandboxing)
    - docker (full container isolation)
    - bubblewrap (Linux namespace sandboxing)
    - subprocess (basic execution with timeout)
    - auto (tries methods in order until one works)
    
    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds
        sandbox_method: Sandbox method to use
        args: Command-line arguments to pass to the Python script
    """
    return execute_sandboxed(code, timeout, method=sandbox_method, args=args)

def create_filename(basename: str) -> str:
    # Create a filename by appending a random suffix to the basename
    random_suffix = str(random.randint(1000, 9999))
    return f"{basename}_{random_suffix}"

# --- Main Agent Function ---
def run_code_agent(use_case: str, goals: str, task_config: dict) -> str:
    coder_model = task_config["coder_model"]
    reviewer_model = task_config["reviewer_model"]
    utility_model = task_config["utility_model"]
    max_iterations = task_config["max_rounds"]
    sandbox_method = task_config.get("sandbox_method", "auto")
    
    print("\n🎯 Use Case:")
    print(use_case)
    print("🎯 Goals:")
    print(goals)

    # Print the task configuration
    print(f"🛠️ Task Configuration: coder_model={coder_model}, reviewer_model={reviewer_model}, utility_model={utility_model}, max_rounds={max_iterations}")

    filename = create_filename(task_config["basename"])
    print(f"🔁 Base name is {filename} for this run")
    
    # Refine the use case and goals before starting
    print("\n🔍 Refining use case and goals before starting...")
    refine_prompt = load_file("scripts/refine task.md")
    refine_response = llm_query(refine_prompt.format_map({
        "use_case": use_case,
        "goals": goals
    }), config=llm_config_refine_task, model=reviewer_model)


    # save the refined response for debugging
    refine_text = refine_response["text"]
    refine_json = json.loads(refine_text)
    save_to_file(f"{filename}_refined_use_text.md", refine_text)
    save_to_file(f"{filename}_refined_use_case.md", refine_json["refined_use_case"])
    save_to_file(f"{filename}_refined_goals.md", refine_json["refined_goals"])
    use_case = refine_json["refined_use_case"]
    goals = refine_json["refined_goals"]  # Keep as list

    previous_code = None
    feedback = None
    for i in range(max_iterations):
        print(f"\n=== 🔁 Iteration {i + 1} of {max_iterations} ===")
        prompt = generate_prompt(use_case, format_goals(goals), previous_code, feedback)
        
        print("🚧 Generating code...")
        code_response = llm_query(prompt, config=llm_config_coder, model=coder_model)
        print_usage_info(code_response["usage"], code_response["response_time"])
        
        print("🧾 Processing LLM output...")
        try:
            # Save JSON response for debugging
            save_to_file(f"{filename}_coder_raw_v{i+1}.json", code_response["full"].model_dump_json(indent=2))
            save_to_file(f"{filename}_coder_text_v{i+1}.md", code_response["text"])

            text = code_response["text"]
            code_blocks = find_code_blocks(text, delimiter="~~~", language="python")
            diff_blocks = find_code_blocks(text, delimiter="~~~", language="diff")
            out_blocks = find_code_blocks(text, delimiter="~~~", language="shell")

            if code_blocks:
                save_to_file(f"{filename}_coder_code_v{i+1}.py", code_blocks[0])
            if diff_blocks:
                save_to_file(f"{filename}_coder_diff_v{i+1}.patch", diff_blocks[0])
            if out_blocks:
                save_to_file(f"{filename}_coder_out_v{i+1}.txt", out_blocks[0])

            # Keep code_output as list for internal processing
            code_output = to_lines(out_blocks[0]) if len(out_blocks) > 0 else []

            if diff_blocks:
                patch_lines = clean_code_block(diff_blocks[0])
                print("🛠️ Detected unified diff patch. Applying patch to previous code.")
                patch_filename = f"{filename}_v{i+1}.patch"

                if previous_code is None:
                    raise ValueError("No previous code to apply patch to.")
                prev_code_lines = to_lines(previous_code)
                patch_code(prev_code_lines, patch_lines)
                code = prev_code_lines  # Now a list
            else:
                if code_blocks:
                    code = clean_code_block(code_blocks[0])  # Now a list
                else:
                    code = []
        except Exception as e:
            print(f"❌ Error processing LLM output: {e}")
            print("Restarting iteration...")
            continue

        code_filename = f"{filename}_v{i+1}.py"
        print(f"💾 Saving intermediate code to file {code_filename}")
        save_to_file(code_filename, code)

        if code_output:
            code_output_filename = f"{filename}_v{i+1}_output.txt"
            print(f"💾 Saving intermediate code output to file {code_output_filename}")
            save_to_file(code_output_filename, code_output)

        # Execute code locally to get actual output
        commandline_args = task_config.get("commandline_args", "")
        print(f"🖥️  Executing code locally (sandbox: {sandbox_method}, args: {commandline_args if commandline_args else 'none'})...")
        local_exec_result = execute_code_locally(to_string(code), sandbox_method=sandbox_method, args=commandline_args)
        local_exec_success = local_exec_result['success']

        actual_method = local_exec_result.get('method', sandbox_method)
        if local_exec_success:
            print(f"✅ Local execution successful, method: {actual_method}")
        else:
            print(f"❌ Local execution returned error: {local_exec_result['stderr']}")

        # Save local execution output
        local_output = local_exec_result['stdout']
        local_output_filename = f"{filename}_v{i+1}_local_output.txt"
        save_to_file(local_output_filename, local_output)

        if not local_exec_success:
            # Save error output for debugging
            error_filename = f"{filename}_v{i+1}_local_error.txt"
            save_to_file(error_filename, f"Exit code: {local_exec_result['exit_code']}\n\nStderr:\n{local_exec_result['stderr']}")

        # Use local output for review if it differs from cloud output
        # Normalize outputs to lists for comparison
        local_output_lines = normalize_output(local_output)
        code_output_lines = normalize_output(code_output) if code_output else []
        
        if code_output and local_output_lines != code_output_lines:
            print(f"⚠️  Local output differs from cloud execution")
            print(f"   Cloud output length: {len(to_string(code_output))} chars")
            print(f"   Local output length: {len(local_output)} chars")
            # Use local output for review since that's what will actually run
            code_output = to_lines(local_output)
        elif not code_output:
            # If no cloud output, use local output
            code_output = to_lines(local_output)



        print("\n📤 Submitting code for feedback review...")
        feedback = get_code_feedback(use_case, to_string(code), format_goals(goals), to_string(code_output), reviewer_model)
        feedback_text = feedback.strip()
        # print("\n📥 Feedback Received:\n" + "-" * 50 + f"\n{feedback_text}\n" + "-" * 50)

        review_filename = f"{filename}_review_v{i+1}.txt"
        print(f"💾 Saving review to file {review_filename}")
        save_to_file(review_filename, feedback_text)

        if goals_met(feedback_text, format_goals(goals), utility_model):
            print("✅ LLM confirms goals are met. Stopping iteration.")
            break

        print("🛠️ Goals not fully met. Preparing for next iteration...")
        previous_code = code

    final_code = add_comment_header(code, use_case, task_config)
    code_filename = f"{filename}.py"
    print(f"💾 Saving final code to file {code_filename}")
    return save_to_file(code_filename, final_code)

# --- CLI Test Run ---
if __name__ == "__main__":
    print("\n🧠 Welcome to the AI Code Generation Agent")

    # Configuration name is the first command-line argument
    config_name = sys.argv[1] if len(sys.argv) > 1 else None

    if not config_name:
        print("Please provide a configuration name as the first argument.")
        sys.exit(1)

    if not os.path.exists(f"tasks/{config_name}/"):
        print(f"Configuration for '{config_name}' not found in 'tasks/{config_name}/'.")
        sys.exit(1)

    # Load task configuration
    task_config = load_task_config(config_name)
    
    use_case_input = load_file(f"tasks/{config_name}/hl_spec.md")
    goals_input = load_file(f"tasks/{config_name}/ac.md")
    run_code_agent(use_case_input, goals_input, task_config)
    