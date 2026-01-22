# Copyright (c) 2025 Andrey Volkov

# This work is a derivative work based on the original by Mahtab Syed.
# Original author copyright notice:
# MIT License
# Copyright (c) 2025 Mahtab Syed
# https://www.linkedin.com/in/mahtabsyed/

from ast import List
import os
import random
import re
import sys
import json
import time
import traceback
import argparse
import asyncio
import logging
import uuid
import subprocess
from pathlib import Path
from google import genai
from google.genai import errors, types
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.planners import PlanReActPlanner, BuiltInPlanner
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams, StdioServerParameters, StreamableHTTPConnectionParams
from patch import patch_code, is_unified_diff
from sandbox_execution import execute_sandboxed
from token_tracker import TokenUsageTracker
from utils import *
from typing import Dict, List, Optional, Union, Tuple, Any
from subagent_base import SubAgentBase

def format_param_value(value):
    """Format parameter values, showing 'N lines' for lists or multiline strings."""
    if isinstance(value, list):
        return f"[{len(value)} lines]"
    elif isinstance(value, str) and '\n' in value:
        line_count = value.count('\n') + 1
        return f"<{line_count} lines>"
    elif isinstance(value, str) and len(value) > 100:
        return f"{value[:100]}..."
    else:
        return str(value)

# Initialize Gemini LLM key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set")


APP_NAME = "coding_agent"
USER_ID = "1234"
# Generate unique session ID for each run to avoid context pollution
SESSION_ID = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"

default_llm_model = "gemini-2.5-flash"
print(f"📡 Initializing Gemini LLM ...")
llm = genai.Client(api_key=api_key)

class Iteration:
    def __init__(self):
        self.code = {}  # Dict of {filepath: content}
        self.coder_summary = None
        self.feedback = None
        self.flags = set()
        self.program_output = None
        self.score = None

    def add_flag(self, name: str):
        self.flags.add(name)
    
    def get_score(self) -> int:
        """Returns the score, or 0 if not set"""
        return self.score if self.score is not None else 0

class Context:
    def __init__(self, filename, use_case, goals):
        self.filename = filename
        self.use_case = use_case
        self.goals = goals
        self.research_summary = ""
        self._iterations = []
        self.current_iteration = None

    @property
    def iterations(self):
        """Returns a copy of the iterations list"""
        return self._iterations.copy()
    
    @property
    def previous(self):
        if len(self._iterations):
            return self._iterations[-1]
        return None

    @property
    def current(self):
        if not self.current_iteration:
            raise RuntimeError("Start an iteration before accessing current")
        return self.current_iteration

    @property
    def iter_no(self):
        return len(self._iterations) + 1

    def start_iteration(self):
        if self.current_iteration:
            self._iterations.append(self.current_iteration)
        self.current_iteration = Iteration()

    def erase_iteration(self):
        self.current_iteration = None

    def trim_iterations(self, limit_by):
        """Trim iterations to keep only the first limit_by iterations.
        The last kept iteration becomes the current iteration."""
        self._iterations = self._iterations[:limit_by]
        if self._iterations:
            self.current_iteration = self._iterations.pop()
        else:
            self.current_iteration = None

    def save_to(self, filename_template, content, content_name=None):
        """
            Saves content to a file with a name based on the template.
            Template parameters are:
                - {name}, which is a solution base name
                - {iter} which is the iteration number.
        """
        try:
            fn = filename_template.format(name=self.filename, iter=self.iter_no)
            save_to_file(fn, content, content_name)
        except KeyError as ke:
            print(f"Error creating file name: key {ke} in the template is invalid: {filename_template}")
            sys.exit(1)

llm_config_coder = genai.types.GenerateContentConfig(
    temperature=1.0,
    tool_config=genai.types.ToolConfig(
        function_calling_config=genai.types.FunctionCallingConfig(
            mode=genai.types.FunctionCallingConfigMode.ANY
        )
    )
)

llm_config_reviewer = genai.types.GenerateContentConfig(
    temperature=0.5,
    response_modalities=["TEXT"],  # Force text output
)

llm_config_research = genai.types.GenerateContentConfig(
    tools=[
        {"url_context": {}}
    ],
    response_modalities=["TEXT"],  # Force text output
    max_output_tokens=50000,  # limit the total output tokens
    thinkingConfig=genai.types.ThinkingConfig(
        thinking_budget=20000,
    )
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



def llm_query(query, parts=None, config=llm_config_coder, model=default_llm_model):
    """
    Query the LLM with retries on server errors.
    Args:
        if parts is None:
            query: The input query string
        else:
            query: System prompt string (will be cached automatically by Gemini if unchanged)
            parts: List of (title, content) tuples to build the prompt
        config: LLM configuration
        model: LLM model name
    """
    max_retries = 10
    
    for attempt in range(max_retries):
        try:
            # mark start time
            start_time = time.monotonic()
            request_config = config
            
            if model.startswith("gemini-3"):
                request_config.temperature = 1.0 # For Gemini 3 it is important not to alter the default temperature

            if parts is None:
                response = llm.models.generate_content(
                    model=model, contents=query, config=request_config
                )
            else:
                # Use system instruction for caching - this gets cached automatically by Gemini
                request_config.system_instruction = query
                
                # Build parts as proper content structure (not concatenated strings)
                request_parts = []
                for title, content in parts:
                    request_parts.append({"text": f"\n\n# {title}\n{content}"})
                
                request_contents = [{"role": "user", "parts": request_parts}]
                
                response = llm.models.generate_content(
                    model=model, contents=request_contents, config=request_config
                )
            end_time = time.monotonic()
            # Calculate generation time in seconds
            generation_time = end_time - start_time
            text = response.text

            # Print usage info and record statistics
            token_tracker.print_call_info(response.usage_metadata, generation_time)
            token_tracker.record(model, response.usage_metadata, generation_time)

            return {"text": text, "full": None, "usage": total_usage, "response_time": generation_time}
        
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

def research(config: dict, context: Context):
    # Refines goals and use case in the context
    refine_prompt = load_file("scripts/research.md")
    if not "urls" in config:
        return False # Nothing to do   
    urls = ", ".join(config["urls"])
    
    response = llm_query(refine_prompt.format_map({
        "use_case": context.use_case,
        "goals": context.goals,
        "urls": urls
    }), config=llm_config_research, model=config["utility_model"])

    # save the refined response for debugging
    context.save_to("{name}_research_raw_{iter}.json", response["full"].model_dump_json(indent=2), content_name="research JSON response" )
    summary = response["text"]
    if not summary:
        print("⚠️  Research step returned empty summary.")
        exit(1)
    else:
        context.save_to("{name}_research_summary_{iter}.md", summary, content_name="research summary")
    context.research_summary = summary or "No research summary available."
    return True

def code(config: dict, context: Context, agent_runner, session_id: str, loop=None, max_tokens: int = 250000):

    if context.previous:
        prompt = load_file("scripts/coder step.md")
        print("🔄 Preparing refinement prompt...")
        
        # Build multi-part message with feedback and execution results
        parts = [("Next step instructions", prompt)]
        
        if context.previous.program_output:
            parts.append(("Previous Execution Results", to_string(context.previous.program_output)))
        if context.previous.feedback:
            parts.append(("Code Review Feedback", to_string(context.previous.feedback)))
        if context.previous.coder_summary:
            parts.append(("Your summary from the previous iteration", to_string(context.previous.coder_summary)))
    else:
        print("📝 Starting initial code generation...")
        # For first iteration, include use case, goals, and optionally research
        parts = [("Task", "Start by creating the initial code implementation.")]
        # Add research summary if it exists and is not the default placeholder
        if context.research_summary:
            parts.append(("Research Summary", context.research_summary))

    # Format as multi-part prompt
    prompt_text = ""
    for i, (title, content) in enumerate(parts):
        if i > 0:
            prompt_text += "\n\n"
        prompt_text += f"# {title}\n{content}"
    
    context.save_to("{name}_coder_prompt_{iter}.md", prompt_text, content_name="coder prompt text")

    try:
        start_time = time.monotonic()
        
        print("🤖 Generating code with agent...")
    
        formatted_parts = [types.Part.from_text(text=f"## {title}\n{content}") for title, content in parts]

        
        # Process events as they arrive using async function
        responses = []
        final_answer = None
        call_token_count = 0  # Track tokens in this specific call
        token_limit_exceeded = False
        
        async def process_agent_events():
            nonlocal final_answer, call_token_count, token_limit_exceeded
            async for event in agent_runner.run_async(user_id=USER_ID, session_id=session_id, new_message=types.Content(role='user', parts=formatted_parts)):
                # print(f"\nDEBUG EVENT: {event}\n")
                try:
                    if hasattr(event, 'content') and hasattr(event.content, 'parts') and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                responses.append(part.text)
                                print(f"🤖 {part.text}", flush=True)
                            if hasattr(part, 'function_call') and part.function_call:
                                params_str = ", ".join(f"{k}={format_param_value(v)}" for k, v in part.function_call.args.items())
                                print(f"📢➡️ Function call: {part.function_call.name}({params_str})", flush=True)
                            if hasattr(part, 'function_response') and part.function_response:
                                resp_data = part.function_response.response
                                # Check for 'success' key first, otherwise fall back to isError
                                if 'success' in resp_data:
                                    is_success = resp_data['success']
                                else:
                                    is_success = not resp_data.get('isError', False)
                                
                                if is_success:
                                    response = "✅ Success"
                                else:
                                    response = "❗Error"
                                    if 'error' in resp_data:
                                        response += f": {resp_data['error']}"
                                print(f"📢↩️ Function response: {response}", flush=True)
                    if event.usage_metadata:
                        token_tracker.print_call_info(event.usage_metadata, 0)  # No time info here
                        token_tracker.record(config["coder_model"], event.usage_metadata, 0)
                        
                        # Track tokens in this call
                        call_token_count += event.usage_metadata.total_token_count or 0
                        
                        # Check if we've exceeded the per-call token limit
                        if call_token_count >= max_tokens and not token_limit_exceeded:
                            print(f"\n⚠️  Token limit for this call reached: {call_token_count:,} / {max_tokens:,}")
                            print("🛑 Stopping agent execution to prevent quality degradation")
                            token_limit_exceeded = True
                            # Set a final answer from what we have so far
                            final_answer = responses[-1] if responses else "Token limit exceeded during execution"
                            break  # Stop processing events
                    
                    if event.is_final_response():
                        final_answer = responses[-1] if responses else ""
                        print("\n🟢 FINAL ANSWER\n", final_answer, "\n")
                except Exception as e:
                    print(f"⚠️  Error processing agent event: {e}")
                    print(f"\nDEBUG EVENT: {event}\n")
        # Run in the persistent event loop to reuse MCP connection
        if loop:
            loop.run_until_complete(process_agent_events())
        else:
            asyncio.run(process_agent_events())
        
        end_time = time.monotonic()
        generation_time = end_time - start_time
        
        # If token limit was exceeded, return False to retry with a fresh session
        if token_limit_exceeded:
            print("❌ Code generation exceeded token limit, will retry with fresh session")
        
        print("🧾 Processing agent output...")
        
        # Create a response dict compatible with existing code
        code_response = {
            "text": final_answer,
            "full": responses,
            # "usage": getattr(response, 'usage_metadata', None),
            "response_time": generation_time
        }
        
        # Save responses for debugging
        # try:
        #     if hasattr(response, 'model_dump_json'):
        #         context.save_to("{name}_coder_raw_{iter}.json", response.model_dump_json(indent=2), content_name="raw agent JSON response")
        #     elif hasattr(response, '__dict__'):
        #         context.save_to("{name}_coder_raw_{iter}.json", json.dumps(response.__dict__, indent=2, default=str), content_name="raw agent JSON response")
        #     else:
        #         context.save_to("{name}_coder_raw_{iter}.json", json.dumps({"text": text, "response_type": str(type(response))}, indent=2), content_name="raw agent JSON response")
        # except Exception as e:
        #     print(f"⚠️  Could not save raw response JSON: {e}")
        #     context.save_to("{name}_coder_raw_{iter}.json", json.dumps({"text": text, "error": str(e)}, indent=2), content_name="raw agent JSON response")
        context.save_to("{name}_coder_text_{iter}.md", final_answer, content_name="raw agent text")
        context.current.coder_summary = final_answer

        # Agent should have saved code using create_file tool
        # Read all Python files from the project directory
        project_path = f"solutions/{context.filename}"
        
        # Directories to skip when reading files
        skip_dirs = {'.venv', '__pycache__', '.git', 'venv', 'env', '.tox', '.pytest_cache', '.ruff_cache'}
        
        print("📝 Reading all files from project directory...")
        context.current.code = {}
        
        if os.path.exists(project_path):
            for root, dirs, files in os.walk(project_path):
                # Filter out directories we want to skip
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for file in files:
                    if file.endswith('.py') or file.endswith('.txt') or file.endswith('.md') or file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, project_path)
                        with open(file_path, 'r') as f:
                            context.current.code[rel_path] = f.read()
                        print(f"   📄 {rel_path}")
        else:
            print("⚠️  Warning: project directory not found")
    except errors.ClientError as e:
        delay = 15 
        print(f"⚠️  Server error during code generation: {e.code} - {e.status}")
        print(f"❌ Message: {e.message}")
        # print(f"❌ Details: {e.details}")
        # Example e.details:
        # {
        #     'error': {
        #         'code': 429, 
        #         'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/usage?tab=rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash-lite\nPlease retry in 52.30073862s.', 
        #         'status': 'RESOURCE_EXHAUSTED', 
        #         'details': [
        #             {'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]},
        #             {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'model': 'gemini-2.5-flash-lite', 'location': 'global'}, 'quotaValue': '20'}]}, 
        #             {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '52s'}
        #         ]
        #     }
        # }

        if e.code == 429:
            for d in e.details["error"].get('details', []): 
                if '@type' in d and d['@type'] == 'type.googleapis.com/google.rpc.RetryInfo':
                    retry_delay = d.get('retryDelay', '15s')
                    delay_match = re.match(r'(\d+)(\.\d+)?s', retry_delay)
                    if delay_match:
                        delay = int(float(delay_match.group(1) + (delay_match.group(2) or '')))
        # add random jitter of up to 5 seconds
        jitter = random.randint(1, 5)
        print(f"🔄 Retrying after {delay}s + {jitter}s...")
        time.sleep(delay + jitter)
        return False
    except Exception as e:
        print(f"❌ Error during code generation: {e}")
        # Print error class name
        print(f"❌ Exception type: {type(e).__name__}")
        traceback.print_exc()
        return False

    return True

def execute(config: dict, context: Context):
    # Execute code locally using the same project folder as MCP
    sandbox_method = config.get("sandbox_method", "auto")
    commandline_args = config.get("commandline_args", "")

    # Use the same project directory that MCP is using
    project_path = f"solutions/{context.filename}"
    
    # Agent already created code.py via MCP tools
    # Just ensure requirements.txt exists if packages specified
    if config.get("python_packages"):
        req_file = os.path.join(project_path, "requirements.txt")
        if not os.path.exists(req_file):
            with open(req_file, 'w') as f:
                f.write('\n'.join(config["python_packages"]))
    
    # Build command arguments: entry point + args
    cmd_args = f"code.py {commandline_args}".strip() if commandline_args else "code.py"
    
    print(f"🖥️  Executing code locally (sandbox: {sandbox_method}, args: {commandline_args if commandline_args else 'none'})...")
    local_exec_result = execute_sandboxed(project_path, cmd_args, method=sandbox_method)
    local_exec_success = local_exec_result['success']

    if local_exec_success:
        context.current.add_flag("exec_success")
        actual_method = local_exec_result.get('method', sandbox_method)
        print(f"✅ Local execution successful using method: {actual_method}")
    else:
        # Distinguish between sandbox failure and program failure
        if local_exec_result.get('sandbox_error', False):
            print(f"❌ Sandbox initialization failed: {local_exec_result['stderr']}")
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

def feedback(config: dict, context: Context) -> str:
    print("🔍 Evaluating code against the goals...")

    script_path = "scripts/reviewer.md"
    system_prompt = load_file(script_path)

    system_parts = [
        ("Use Case", context.use_case),
        ("Research Summary", context.research_summary)
    ]
    user_parts = [
        ("Goals", context.goals)
    ]    

    if context.current.code:
        # Format all files with their names
        code_text = ""
        for filepath, content in sorted(context.current.code.items()):
            code_text += f"\n\n### File: {filepath}\n\n"
            code_text += f"```python\n{content}\n```"
        user_parts.append(("Code from this iteration", code_text))
    if context.current.program_output:
        user_parts.append(("Code execution output", to_string(context.current.program_output)))
    if context.previous and context.previous.feedback:
        user_parts.append(("Your previous review", to_string(context.previous.feedback)))

    for title, content in system_parts:
        system_prompt += f"\n\n# {title}\n{content}"

    prompt_text = system_prompt
    for title, content in user_parts:
        prompt_text += f"\n\n# {title}\n{content}"
    context.save_to("{name}_review_prompt_{iter}.md", prompt_text, content_name="reviewer prompt text")

    context.current.feedback = llm_query(system_prompt, parts=user_parts, 
                                         config=llm_config_reviewer, model=config["reviewer_model"])["text"]
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
    
    # First try to parse as JSON, then fallback to extracting json code block
    try:
        json_block = to_string(clean_code_block(response_text))
        response_json = json.loads(json_block)
        result = response_json.get("result", "No").lower()
        score = response_json.get("score", 0)
        return (result == "yes", score)
    except json.JSONDecodeError:
        print(f"⚠️  Failed to parse goals check response as JSON, retrying with code block extraction...")

    try:
        json_blocks = find_code_blocks(response_text, delimiter="```", language="json")
        if json_blocks:
            json_block = to_string(clean_code_block(json_blocks[0]))
            response_json = json.loads(json_block)
            result = response_json.get("result", "No").lower()
            score = response_json.get("score", 0)
            return (result == "yes", score)
        else:
            print(f"⚠️  No code blocks found in response")
    except (json.JSONDecodeError, IndexError) as e:
        print(f"⚠️  Failed to parse goals check response as JSON: {response_text}")

    return (False, 0)

def restore_iteration_files(context: Context, project_path: str):
    """
    Restores files from the current iteration context to the project directory.
    Deletes all existing Python files first.
    """
    # Delete all existing Python files
    if os.path.exists(project_path):
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    print(f"   🗑️  Deleted {os.path.relpath(file_path, project_path)}")
    
    # Restore files from context
    os.makedirs(project_path, exist_ok=True)
    for rel_path, content in context.current.code.items():
        file_path = os.path.join(project_path, rel_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"   ✅ Restored {rel_path}")

def progress_check(context: Context, reset_threshold: int) -> int:
    """ 
    Checks if there is progress in scores.
    If there is no progress over the last 3 iterations, returns the iteration number to return to.
    """
    # Calculate score sequence - use get_score() to handle None
    scores = [x.get_score() for x in context.iterations]
    scores.append(context.current.get_score())
    if len(scores) < reset_threshold:
        return None  # Not enough data to determine
    # Find last best score index (rightmost), and if it's older than reset_threshold iterations, return that index
    best_score = max(scores)
    # Find this score from the right
    best_index = len(scores) - 1 - scores[::-1].index(best_score)
    if best_index < len(scores) - reset_threshold:
        return best_index
    return None


def create_readme(config: dict, context: Context, token_tracker: TokenUsageTracker, project_path: str) -> str:
    """
    Creates a README.md file in the project directory with metadata.
    """
    readme_content = []
    readme_content.append(f"# Generated by AI Code Generation Agent\n")
    readme_content.append(f"This Python program implements the following use case:\n")
    use_case_lines = to_lines(context.use_case)
    for line in use_case_lines:
        readme_content.append(f"- {line.strip()}\n")
    readme_content.append(f"It shall meet the following goals:\n")
    goals_lines = to_lines(context.goals)
    for line in goals_lines:
        readme_content.append(f"- {line.strip()}\n")
    readme_content.append(f"Models used: coder={config['coder_model']}, reviewer={config['reviewer_model']}, utility={config['utility_model']}\n")
    readme_content.append(f"It required {len(context.iterations) + 1} coding rounds to complete.\n")
    readme_content.append(f"Token usage summary:\n")
    for line in token_tracker.summary():
        readme_content.append(f"{line}\n")
    
    readme_path = os.path.join(project_path, "README.md")
    with open(readme_path, 'w') as f:
        f.write(''.join(readme_content))
    
    print(f"📝 Created {readme_path}")
    return project_path

def create_filename(basename: str) -> str:
    # Create a filename by appending a random suffix to the basename
    random_suffix = str(random.randint(1000, 9999))
    return f"{basename}_{random_suffix}"

def wait_mcp_operation_complete(mcp_toolset, loop, max_retries=20, delay=5):
    """
    Wait for MCP server to be ready by attempting to get tools.
    Returns True if MCP is ready or not started, False if timed out.
    """
    for attempt in range(max_retries):
        try:
            async def check_tools():
                await asyncio.wait_for(mcp_toolset.get_tools(), timeout=2.0)
            
            loop.run_until_complete(check_tools())
            if attempt > 0:
                print(f"✅ MCP server ready after {attempt + 1} retries ({(attempt + 1) * delay}s)")
            return True
        except asyncio.TimeoutError:
            # MCP is busy with long-running operation
            if attempt == 0:
                print("⏳ MCP server is busy with long-running operation, waiting for completion...")
            elif attempt < max_retries - 1:
                print(f"⏳ Still waiting... (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
        except Exception as e:
            # MCP not started yet or connection error - skip waiting
            error_str = str(e).lower()
            if "not responding" in error_str or "connection" in error_str or "failed to get tools" in error_str:
                print(f"ℹ️  MCP server not running")
                return True
            # Other unexpected errors
            if attempt < max_retries - 1:
                print(f"⚠️  Unexpected error, retrying: {e}")
                time.sleep(delay)
    
    print(f"❌ MCP server not responding after {max_retries * delay}s")
    return False

class MCPInstance():
    process = None
    def __init__(self, project_path: str):
        self.project_path = project_path
        if MCPInstance.process is not None:
            raise RuntimeError("MCPInstance already running")
        MCPInstance.process = None

    def start(self):
        os.makedirs(self.project_path, exist_ok=True)
        
        print("\n🔌 Starting MCP server in HTTP mode...")
        mcp_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
        self.mcp_host = "127.0.0.1"
        self.mcp_port = 8000
        
        # Start MCP server as a subprocess in HTTP mode
        MCPInstance.process = subprocess.Popen(
            [sys.executable, mcp_script, self.project_path, "--transport", "http", "--host", self.mcp_host, "--port", str(self.mcp_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give server time to start
        time.sleep(3)

    def get_toolset(self):
        return McpToolset(
                connection_params=StreamableHTTPConnectionParams(
                    url=f"http://{self.mcp_host}:{self.mcp_port}/mcp",
                    timeout=60.0,
                    sse_read_timeout=300.0,
                    terminate_on_close=False  # We'll manage termination in finally block
                )            
            )

    def stop(self):
        # Terminate MCP server
        if MCPInstance.process:
            print("🛑 Stopping MCP server...")
            MCPInstance.process.terminate()
            try:
                MCPInstance.process.wait(timeout=5)
                print("✅ MCP server stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  MCP server did not stop gracefully, killing...")
                MCPInstance.process.kill()
                MCPInstance.process.wait()


# --- Main Agent Function ---
def run_code_agent(task_config: dict, use_case: str, goals: str, flag_refine_goals: bool = True, reset_threshold: int = 3, max_tokens_per_call: int = 250000) -> str:
    max_iterations = task_config["max_rounds"]
    
    print("\n🎯 Use Case:")
    print(use_case)
    print("🎯 Goals:")
    print(goals)

    # Print the task configuration
    print(f"🛠️ Task Configuration: coder_model={task_config['coder_model']}, reviewer_model={task_config['reviewer_model']}, utility_model={task_config['utility_model']}, max_rounds={max_iterations}, max_tokens_per_call={max_tokens_per_call:,}")

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

    if "python_packages" in task_config:
        print(f"📦 Additional Python packages to install in sandbox: {task_config['python_packages']}")
        context.use_case += f"\n\nThe following extra Python packages will be available for use: {', '.join(task_config['python_packages'])}\n"

    # Call research step if URLs are provided
    if "urls" in task_config:
        print("\n🔬 Performing research using provided URLs...")
        research(task_config, context)

    # Start MCP server once before all iterations
    project_path = f"solutions/{filename}"
    os.makedirs(project_path, exist_ok=True)
    
    print("\n🔌 Starting MCP server in HTTP mode...")
    mcp_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
    mcp_host = "127.0.0.1"
    mcp_port = 8000
    
    # Start MCP server as a subprocess in HTTP mode
    mcp_process = subprocess.Popen(
        [sys.executable, mcp_script, project_path, "--transport", "http", "--host", mcp_host, "--port", str(mcp_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Verify server started successfully
    print("⏳ Waiting for MCP server to start...")
    for i in range(10):
        time.sleep(0.5)
        if mcp_process.poll() is not None:
            # Process died
            stdout, stderr = mcp_process.communicate()
            print(f"❌ MCP server failed to start (exit code: {mcp_process.returncode})")
            if stderr:
                print(f"Error output: {stderr}")
            raise RuntimeError(f"MCP server process exited prematurely")
    
    print(f"✅ MCP server running at http://{mcp_host}:{mcp_port}/mcp")
    
    # Build system instruction with context
    system_instruction_template = load_file("scripts/coder init.md")
    system_instruction = system_instruction_template.format(
        use_case=context.use_case,
        goals=context.goals
    )

    # Suppress verbose logging from base_authenticated_tool (it will cry that there is no auth config)
    logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)
    
    print("🔌 Creating Gemini agent with MCP tools...")
    # Create agent once - it will connect to the HTTP MCP server
    coding_agent = LlmAgent(
        model=task_config["coder_model"],
        name='code_generator',
        instruction=system_instruction,
        generate_content_config=llm_config_coder,
        planner=PlanReActPlanner(),
        # planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(
        #     include_thoughts=True,
        #     thinking_budget=15000,
        # )),
        tools=[
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(
                    url=f"http://{mcp_host}:{mcp_port}/mcp",
                    timeout=60.0,
                    sse_read_timeout=300.0,
                    terminate_on_close=False  # We'll manage termination in finally block
                )            
            )
        ]
    )
    coding_session_service = InMemorySessionService()
    coding_session = asyncio.run(coding_session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID))
    coding_agent_runner = Runner(agent=coding_agent, app_name=APP_NAME, session_service=coding_session_service)

    print("✅ Agent created and ready")

    # Create a persistent event loop for all iterations to avoid MCP connection recreation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        for i in range(max_iterations):
            print(f"\n=== 🔁 Iteration {i + 1} of {max_iterations} ===")

            context.start_iteration()

            # Create fresh session for this iteration to prevent context overflow
            iteration_session_id = f"{SESSION_ID}_iter_{i+1}"
            print(f"🔄 Creating fresh session: {iteration_session_id}")
            loop.run_until_complete(
                coding_session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=iteration_session_id
                )
            )

            # Run coding stage with agent (pass loop and session_id)
            code_result = code(task_config, context, agent_runner=coding_agent_runner, 
                       session_id=iteration_session_id, loop=loop, max_tokens=max_tokens_per_call)

            # Wait for MCP server to complete any pending operations
            wait_mcp_operation_complete(coding_agent.tools[0], loop)

            if not code_result:
                context.erase_iteration()
                print("❌ Model generated some bad output, repeating iteration")
                continue

            # Execute code
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

            if reset_threshold > 0:
                return_to_iteration = progress_check(context, reset_threshold)
                if return_to_iteration is not None:
                    context.trim_iterations(return_to_iteration+1)
                    if "restarted_from_no_progress" not in context.current.flags:
                        print(f"🔄 No progress detected. Resetting to iteration {return_to_iteration + 1} and continuing from there.")
                        context.current.add_flag("restarted_from_no_progress")
                    else:
                        print("⚠️  No progress detected again after restart. Restarting from step 1.")
                        context.trim_iterations(0)
                    
                    # Restore files from the iteration we're rolling back to
                    print(f"📁 Restoring files from iteration {return_to_iteration + 1}...")
                    restore_iteration_files(context, project_path)
    finally:
        # Close the event loop
        loop.close()
        print("🔌 Closed event loop and MCP connections")
        
        # Terminate MCP server
        if 'mcp_process' in locals() and mcp_process:
            print("🛑 Stopping MCP server...")
            mcp_process.terminate()
            try:
                mcp_process.wait(timeout=5)
                print("✅ MCP server stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  MCP server did not stop gracefully, killing...")
                mcp_process.kill()
                mcp_process.wait()

    # Print token usage summary
    token_tracker.print_summary()

    # Create README.md in the project folder
    final_project_path = create_readme(task_config, context, token_tracker, project_path)
    print(f"\n✅ Code generation complete. Project saved to: {final_project_path}")
    return final_project_path

def test_streaming_agent():
    # Copy test files to solutions/test_streaming_agent
    import shutil
    if os.path.exists("solutions/test_streaming_agent"):
        shutil.rmtree("solutions/test_streaming_agent")
    shutil.copytree("test_sets/test_streaming_agent", "solutions/test_streaming_agent")

    mcp = MCPInstance(project_path="solutions/test_streaming_agent")
    mcp.start()

    llm_config = genai.types.GenerateContentConfig(
        temperature=1.0,
    )

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
Your response is a summary of your work. Structure it as follows:

1. **What I completed**: Describe what you implemented (fixes made, files changed, etc.)
2. **What could not be fixed**: Brief summary of what could not be fixed (if any)
    """



    try:
        subagent = SubAgentBase(
            llm=llm,
            model="gemini-2.5-flash-lite", 
            token_tracker=token_tracker,
            base_config=llm_config, 
            system_instruction=system_instruction, 
            mcp_toolset=mcp.get_toolset(),
            allowed_mcp_tools=[
                "list_files",
                "get_line_range",
                "search_files",
                "find_python_definition",
                "replace_in_files",
                "fuzzy_replace_in_file",
                "multiline_replace_in_file",
                "run_ruff_check"
            ]
        )
        
        subagent.query(query="Fix all syntax errors in the project code.", debug=True)
    finally:
        mcp.stop()
        # Print token usage summary
        token_tracker.print_summary()


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
    parser.add_argument("--reset", type=int, help="Number of unsuccessful operations before resetting the the last successful iteration")
    parser.add_argument("--no-reset", dest="reset", action="store_const", const=0,
                        help="Disable resetting on no progress")
    parser.add_argument("--max-tokens-per-call", type=int, default=250000,
                        help="Maximum tokens per single code() call before stopping (default: 250,000)")
    parser.set_defaults(refine_goals=True)
    parser.set_defaults(reset=3)
    args = parser.parse_args()
    config_name = args.config_name

    if not os.path.exists(f"tasks/{config_name}/"):
        print(f"Configuration for '{config_name}' not found in 'tasks/{config_name}/'.")
        sys.exit(1)

    # Load task configuration
    task_config = load_task_config(config_name)
    
    use_case_input = load_file(f"tasks/{config_name}/hl_spec.md")
    goals_input = load_file(f"tasks/{config_name}/ac.md")
    # run_code_agent(task_config, use_case_input, goals_input, flag_refine_goals=args.refine_goals, reset_threshold=args.reset, max_tokens_per_call=args.max_tokens_per_call)

    test_streaming_agent()