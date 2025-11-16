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
import argparse
from pathlib import Path
from google import genai
from google.genai import errors
from patch import patch_code, is_unified_diff
from md_parser import find_code_blocks
from sandbox_execution import execute_sandboxed
from token_tracker import TokenUsageTracker
from utils import *

# Initialize Gemini LLM key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set")

default_llm_model = "gemini-2.5-flash"
print(f"📡 Initializing Gemini LLM ...")
llm = genai.Client(api_key=api_key)

class Iteration:
    def __init__(self):
        self.code = None
        self.feedback = None
        self.flags = set()
        self.program_output = None
        self.score = None

    def add_flag(self, name: str):
        self.flags.add(name)

class Context:
    def __init__(self, filename, use_case, goals):
        self.filename = filename
        self.use_case = use_case
        self.goals = goals
        self.iterations = []
        self.current_iteration = None
    
    @property
    def previous(self):
        if len(self.iterations):
            return self.iterations[-1]
        return None

    @property
    def current(self):
        if not self.current_iteration:
            self.start_iteration()
        return self.current_iteration

    @property
    def iter_no(self):
        return len(self.iterations) + 1

    def start_iteration(self):
        if self.current_iteration:
            self.iterations.append(self.current_iteration)
        self.current_iteration = Iteration()

    def erase_iteration(self):
        self.current_iteration = None

    def save_to(self, filename_template, content, content_name=None):
        """
            Saves content to a file with a name based on the template.
            Template parameters are:
                - {name}, which is a solution base name
                - {iter} which is iteration number.
        """
        try:
            fn = filename_template.format(name=self.filename, iter=self.iter_no)
            save_to_file(fn, content, content_name)
        except KeyError as ke:
            print(f"Error creating file name: key {ke} in template is wrong: {filename_template}")
            sys.exit(1)
            
llm_config = genai.types.GenerateContentConfig(
    temperature=0.3,
    tools=[genai.types.Tool(code_execution=genai.types.ToolCodeExecution)]
)

llm_config_coder = genai.types.GenerateContentConfig(
    temperature=0.3,
    tools=[genai.types.Tool(code_execution=genai.types.ToolCodeExecution), 
           genai.types.Tool(google_search=genai.types.GoogleSearch()),
           {"url_context": {}}
       ],
)

llm_config_goals_check = genai.types.GenerateContentConfig(
    temperature=0.3,
    responseMimeType="text/x.enum",
    responseSchema={
        "type": "object",
        "properties": {
            "result": {
                "type": "string",
                "enum": ["Yes", "No"],
                "description": "Whether the goals have been met"
            },
            "score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Completion score (0-100) of the solution against the goals"
            }
        }
    }
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

# Initialize token usage tracker
token_tracker = TokenUsageTracker()

def llm_query(query, config=llm_config, model=default_llm_model):
    max_retries = 10
    
    for attempt in range(max_retries):
        try:
            # mark start time
            start_time = time.monotonic()
            response = llm.models.generate_content(
                model=model, contents=query, config=config
            )
            end_time = time.monotonic()
            # Calculate generation time in seconds
            generation_time = end_time - start_time
            text = response.text

            # Print usage info and record statistics
            token_tracker.print_call_info(response.usage_metadata, generation_time)
            token_tracker.record(model, response.usage_metadata, generation_time)

            return {"text": text, "full": response, "usage": response.usage_metadata, "response_time": generation_time}
        
        except errors.ServerError as e:
            if attempt < max_retries - 1:
                # 15 seconds for 503, 5 seconds for other 5xx errors
                delay = 15 if e.code == 503 else 5
                print(f"⚠️  Server error: {e}")
                print(f"🔄 Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"❌ Server error after {max_retries} retries: {e}")
                raise

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

def refine_goals(config: dict, context: Context):
    # Refines goals and use case in the context
    refine_prompt = load_file("scripts/refine task.md")
    refine_response = llm_query(refine_prompt.format_map({
        "use_case": context.use_case,
        "goals": context.goals
    }), config=llm_config_refine_task, model=config["reviewer_model"])

    # save the refined response for debugging
    refine_text = refine_response["text"]
    refine_json = json.loads(refine_text)
    context.save_to("{name}_refined_use_case.md", refine_json["refined_use_case"], content_name="refined use case")
    context.save_to("{name}_refined_goals.md", refine_json["refined_goals"], content_name="refined goals")
    context.use_case = refine_json["refined_use_case"]
    context.goals = refine_json["refined_goals"]  # Keep as list
    return True

def code(config: dict, context: Context):

    if context.previous:
        print("🔄Creating code refinement prompt...")
        script_path = "scripts/coder fix.md"
    else:
        print("📝 Constructing code generation prompt...")
        script_path = "scripts/coder create.md"

    script = load_file(script_path)
            
    prompt = script.format_map({
        "use_case": context.use_case,
        "goals": context.goals,
        "previous": context.previous
    })
    context.save_to("{name}_coder_prompt_{iter}.md", prompt, content_name="coder prompt")

    print("🚧 Generating code...")
    code_response = llm_query(prompt, config=llm_config_coder, model=config["coder_model"])
    
    print("🧾 Processing LLM output...")
    # Save JSON response for debugging
    context.save_to("{name}_coder_raw_{iter}.json", code_response["full"].model_dump_json(indent=2), content_name="raw LLM JSON response" )
    context.save_to("{name}_coder_text_{iter}.md", code_response["text"], content_name="raw LLM text")

    # Check if LLM actually executed code
    response_obj = code_response["full"]
    if hasattr(response_obj, 'candidates') and response_obj.candidates:
        parts = response_obj.candidates[0].content.parts
        for part in parts:
            if hasattr(part, 'code_execution_result') and part.code_execution_result:
                context.current.add_flag('llm_executed')
                break

    if not 'llm_executed' in context.current.flags:
        print("⚠️  WARNING: LLM did not execute code (the code may be non-runnable)")

    text = code_response["text"]
    code_blocks = find_code_blocks(text, delimiter="~~~", language="python")
    diff_blocks = find_code_blocks(text, delimiter="~~~", language="diff")

    if code_blocks:
        context.save_to("{name}_coder_code_{iter}.py", code_blocks[0], content_name="code block")
    if diff_blocks:
        context.save_to("{name}_coder_diff_{iter}.patch", diff_blocks[0], content_name="diff patch")

    if diff_blocks and context.previous and context.previous.code:
        if not code_quality_gate(diff_blocks[0]):
            return False
        patch_lines = clean_code_block(diff_blocks[0])
        print("🛠️ Detected unified diff patch. Applying patch to previous code.")
        prev_code_lines = to_lines(context.previous.code)
        patch_code(prev_code_lines, patch_lines)
        context.current.code = prev_code_lines 
    elif code_blocks:
        if not code_quality_gate(code_blocks[0]):
            return False
        context.current.code = clean_code_block(code_blocks[0])  # Now a list
    else:
        context.current.code = []

    context.save_to("{name}_v{iter}.py", context.current.code, content_name="intermediate code")
    return True

def execute(config: dict, context: Context):
    # Execute code locally and get actual program output and/or errors
    sandbox_method = config.get("sandbox_method", "auto")
    commandline_args = config.get("commandline_args", "")
    
    print(f"🖥️  Executing code locally (sandbox: {sandbox_method}, args: {commandline_args if commandline_args else 'none'})...")
    local_exec_result = execute_sandboxed(to_string(context.current.code), method=sandbox_method, args=commandline_args)
    local_exec_success = local_exec_result['success']

    if local_exec_success:
        context.current.add_flag("exec_success")
        actual_method = local_exec_result.get('method', sandbox_method)
        print(f"✅ Local execution successful using method: {actual_method}")
    else:
        print(f"❌ Local execution returned error: {local_exec_result['stderr']}")

    # Check if there were obvious syntax errors
    if "SyntaxError" in local_exec_result['stderr']  or "IndentationError" in local_exec_result['stderr']:
        context.current.add_flag("syntax_error")

    # Save local execution output
    program_output = ["Program exited with code " + str(local_exec_result['exit_code'])]
    program_output.extend(["", "Stdout:", "", "~~~shell"])
    program_output.extend(to_lines(local_exec_result['stdout']))
    program_output.extend(["~~~", "", "Stderr:", "", "~~~shell"])
    program_output.extend(to_lines(local_exec_result['stderr']))
    program_output.extend(["~~~"])

    context.save_to("{name}_v{iter}_output.txt", program_output, content_name="local execution output")
    context.current.program_output = program_output

def fix_syntax_errors(config: dict, context: Context):
    # Run syntax fix step. The model does not know anything about the goals, it has to merely fix syntax issues
    print("\n🚨 SyntaxError or IndentationError detected in program output. Running syntax fix iteration...")
    context.current.add_flag("syntax_fix")
    # load prompt for syntax fix
    syntax_fix_prompt = load_file("scripts/syntax fix.md")
    syntax_fix_prompt_formatted = syntax_fix_prompt.format_map({
        "previous_code": to_string(context.current.code),
        "program_output": to_string(context.current.program_output)
    })
    context.save_to("{name}_syntax_fix_prompt_v{iter}.md", syntax_fix_prompt_formatted, content_name="syntax fix prompt")
    syntax_fix_response = llm_query(syntax_fix_prompt_formatted, model=config["coder_model"]) # Or utility_model?
    syntax_fix_text = syntax_fix_response["text"]
    context.save_to("{name}_syntax_fix_response_v{iter}.md", syntax_fix_text, content_name="syntax fix response")
    diff_blocks = find_code_blocks(syntax_fix_text, delimiter="~~~", language="diff")
    if diff_blocks:
        print("🛠️ Applying syntax fix diff patch to current code.")
        patch_lines = clean_code_block(diff_blocks[0])
        code_lines = to_lines(context.current.code)
        patch_code(code_lines, patch_lines)
        context.current.code = code_lines 
        # Save fixed code
        context.save_to("{name}_v{iter}_syntax_fixed.py", context.current.code, content_name="syntax fixed code")
        return True
    else:
        return False

def feedback(config: dict, context: Context) -> str:
    print("🔍 Evaluating code against the goals...")

    script_path = "scripts/reviewer.md"
    script = load_file(script_path)
    feedback_prompt = script.format_map({
        "use_case": context.use_case,
        "goals": context.goals,
        "code": context.current.code,
        "code_output": context.current.program_output
    })
    context.current.feedback = llm_query(feedback_prompt, model=config["reviewer_model"])["text"]
    if context.current.feedback:
        context.save_to("{name}_review_v{iter}.txt", context.current.feedback, content_name="code review")
        return True
    return False

def goals_met(config: dict, context: Context) -> tuple[bool, int]:
    """
    Uses the LLM to evaluate whether the goals have been met based on the feedback text.
    Returns tuple of (goals_met: bool, score: int).
    """
    script_path = "scripts/goals check.md"
    script = load_file(script_path)
    review_prompt = script.format_map({
        "goals": context.goals,
        "feedback_text": context.current.feedback
    })
    response_text = llm_query(review_prompt, config=llm_config_goals_check, model=config["utility_model"])["text"]
    
    try:
        response_json = json.loads(to_string(clean_code_block(response_text)))
        result = response_json.get("result", "No").lower()
        score = response_json.get("score", 0)
        return (result == "yes", score)
    except json.JSONDecodeError:
        print(f"⚠️  Failed to parse goals check response as JSON: {response_text}")
        return (False, 0)

def format_final_code(config: dict, context: Context, token_tracker: TokenUsageTracker) -> list:
    """
    Add comment header to code.
    """
    comment = []
    comment.append(f"# Generated by AI Code Generation Agent")
    comment.append(f"# This Python program implements the following use case:")
    use_case_lines = to_lines(context.use_case)
    for line in use_case_lines:
        comment.append(f"# {line.strip()}")
    comment.append(f"# It shall meet the following goals:")
    goals_lines = to_lines(context.goals)
    for line in goals_lines:
        comment.append(f"# {line.strip()}")
    comment.append(f"# Models used: coder={config['coder_model']}, reviewer={config['reviewer_model']}, utility={config['utility_model']}")
    comment.append(f"# It required {len(context.iterations) + 1} coding rounds to complete.")
    comment.append(f"# Token usage summary:")
    for line in token_tracker.summary():
        comment.append(f"# {line}")
    comment.append("")
    
    code_lines = to_lines(context.current.code)
    return comment + code_lines

def create_filename(basename: str) -> str:
    # Create a filename by appending a random suffix to the basename
    random_suffix = str(random.randint(1000, 9999))
    return f"{basename}_{random_suffix}"

# --- Main Agent Function ---
def run_code_agent(task_config: dict, use_case: str, goals: str, flag_refine_goals: bool = True) -> str:
    max_iterations = task_config["max_rounds"]
    
    print("\n🎯 Use Case:")
    print(use_case)
    print("🎯 Goals:")
    print(goals)

    # Print the task configuration
    print(f"🛠️ Task Configuration: coder_model={task_config['coder_model']}, reviewer_model={task_config['reviewer_model']}, utility_model={task_config['utility_model']}, max_rounds={max_iterations}")

    filename = create_filename(task_config["basename"])
    print(f"🔁 Base name is {filename} for this run")
    context = Context(filename, use_case, goals)

    # Refine the use case and goals before starting (if enabled)
    if flag_refine_goals:
        print("\n🔍 Refining use case and goals before starting...")
        refine_goals(task_config, context)
    else:
        print("\n⏭️  Skipping goals refinement (using original goals)")
    
    # Format goals as a string with a bullet list inside
    context.goals = format_goals(context.goals)

    # Append URLs to the use case if provided in task config
    if "urls" in task_config:
        context.use_case += f"\n\nThe following URLs provide additional context:\n"
        for url in task_config["urls"]:
            context.use_case += f"- {url}\n"

    for i in range(max_iterations):
        print(f"\n=== 🔁 Iteration {i + 1} of {max_iterations} ===")

        context.start_iteration()

        # Run coding stage
        if not code(task_config, context):
            context.erase_iteration()
            print("❌ Model generated some bad output, repeating iteration")
            continue

        # Execute code
        execute(task_config, context)

        # If there were syntax errors, run one round of fixing them
        if "syntax_error" in context.current.flags:
            if fix_syntax_errors(task_config, context):
                # If there were successful changes, execute once more
                execute(task_config, context)


        print("\n📤 Submitting code for feedback review...")
        if not feedback(task_config, context):
            print("❌ No feedback received, repeating iteration...")
            context.erase_iteration()
            continue

        done_flag, score = goals_met(task_config, context)
        context.current.score = score

        if done_flag:
            print("✅ LLM confirms goals are met. Stopping iteration.")
            break

        print("🛠️ Goals not fully met. Preparing for next iteration...")
        # Create scores from context
        scores = [x.score for x in context.iterations]
        scores.append(context.current.score)
        print(f"📊 Completion score progression: {scores}")

    # Print token usage summary
    token_tracker.print_summary()

    final_code = format_final_code(task_config, context, token_tracker)
    code_filename = f"{filename}.py"
    return save_to_file(code_filename, final_code, content_name="final code")

# --- CLI Test Run ---
if __name__ == "__main__":
    print("\n🧠 Welcome to the AI Code Generation Agent")

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="AI Code Generation Agent")
    parser.add_argument("config_name", help="Configuration name (task directory in tasks/)")
    parser.add_argument("--refine-goals", dest="refine_goals", action="store_true", 
                        help="Refine use case and goals before starting (default)")
    parser.add_argument("--no-refine-goals", dest="refine_goals", action="store_false",
                        help="Skip goals refinement, use original goals as-is")
    parser.set_defaults(refine_goals=True)
    
    args = parser.parse_args()
    config_name = args.config_name

    if not os.path.exists(f"tasks/{config_name}/"):
        print(f"Configuration for '{config_name}' not found in 'tasks/{config_name}/'.")
        sys.exit(1)

    # Load task configuration
    task_config = load_task_config(config_name)
    
    use_case_input = load_file(f"tasks/{config_name}/hl_spec.md")
    goals_input = load_file(f"tasks/{config_name}/ac.md")
    run_code_agent(task_config, use_case_input, goals_input, flag_refine_goals=args.refine_goals)
    