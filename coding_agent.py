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
from pathlib import Path
from google import genai

# Initialize Gemini LLM
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set")

llm_model = "gemini-2.5-flash"
print(f"📡 Initializing Gemini LLM ({llm_model})...")
llm = genai.Client(api_key=api_key)
llm_config = genai.types.GenerateContentConfig(
#    system_instruction='I say high, you say low',
#    max_output_tokens=3,
    temperature=0.3,
    tools=[genai.types.Tool(code_execution=genai.types.ToolCodeExecution)]
)

def llm_query(query):
    response = llm.models.generate_content(
        model=llm_model, contents=query, config=llm_config
    )
    # If there are multiple parts, return them as a list
    text = response.text
    code = None
    output = None
    result = None
    
    # print(response)
    for part in response.candidates[0].content.parts:
        if part.executable_code:
            code = part.executable_code.code
        if part.code_execution_result:
            output = part.code_execution_result.output
            result = part.code_execution_result.outcome
    
    return {"text": text, "code": code, "output": output, "result": result}

# --- Utility Functions ---
def load_file(filepath: str) -> str:
    with open(filepath, "r") as f:
        return f.read()

def generate_prompt(use_case: str, goals: str, previous_code: str = "", feedback: str = "") -> str:
    print("📝 Constructing prompt for code generation...")
    base_prompt = f"""
        You are an AI coding agent. Your job is to write Python code based on the following use case:
        # Use Case: 
        {use_case}
        
        # Your goals are:
        {goals}
    """
    if previous_code:
        print("🔄 Adding previous code to the prompt for refinement.")
        base_prompt += f"\nPreviously generated code:\n{previous_code}"
    if feedback:
        print("📋 Including feedback for revision.")
        base_prompt += f"\nFeedback on previous version:\n{feedback}\n"
    base_prompt += "\nPlease return only the revised Python code. Do not include comments or explanations outside the code."
    return base_prompt

def get_code_feedback(code: str, goals: str, code_execution: str, code_execution_result: str) -> str:
    print("🔍 Evaluating code against the goals...")
    feedback_prompt = f"""
You are a Python code reviewer. A code snippet is shown below. Based on the following goals:
{goals}
Also provided are the results of executing the program and its output.
Please critique this code and identify if the goals are met. 
Examine unit test output listed in the Program output run and identify if there are any failures or issues. Specifically request to fix all failed tests by listing them clearly.
Mention if improvements are needed for clarity, simplicity, correctness, edge case handling, or test coverage.
Avoid polite language; be direct and specific about what needs to be improved. Classify issues as Minor, Major, or Critical. 
Here, Minor means small improvements, that may be or may be not implemented after your review.
Major means significant changes needed and they have to be implemented, and Critical means the code does not meet the goal at all.
If the code seems totally broken and you don't think it can be fixed, use its_totally_broken(issue) tool to report the issue.
Code:
{code}

Program Execution Result:
{code_execution_result}

Program output:
{code_execution}
"""
    return llm_query(feedback_prompt)["text"]

def goals_met(feedback_text: str, goals: str) -> bool:
    """
    Uses the LLM to evaluate whether the goals have been met based on the feedback text.
    Returns True or False (parsed from LLM output).
    """
    review_prompt = f"""
        You are an AI reviewer.
        Here are the goals:
        {goals}
        Here is the feedback on the code:
        \"\"\"
        {feedback_text}
        \"\"\"
        Based on the feedback above, have the goals been met? If there are any unmet goals, respond with False. 
        If there are corrections needed, return False. If there are any issues higher then Minor, return False.
        If some goals are only partially (or mostly) met, respond with False.
        Otherwise, respond with True.
        Respond with only one word: True or False.
    """
    response = llm_query(review_prompt)["text"].strip().lower()
    return response == "true"

def clean_code_block(code: str) -> str:
    lines = code.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()

def add_comment_header(code: str, use_case: str) -> str:
    comment = []
    comment.append(f"# This Python program implements the following use case:")
    for line in use_case.strip().splitlines():
        comment.append(f"# {line.strip()}")
    comment.append(f"# Generated by AI Code Generation Agent using {llm_model}\n")
    return "\n".join(comment) + "\n" + code

def to_snake_case(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9 ]", "", text)
    return re.sub(r"\s+", "_", text.strip().lower())

def create_short_filename(use_case: str) -> str:
    summary_prompt = (
        f"Summarize the following use case into a single lowercase word or phrase, "
        f"no more than 10 characters, suitable for a Python filename:\n\n{use_case}"
    )
    raw_summary = llm_query(summary_prompt)["text"].strip()
    short_name = re.sub(r"[^a-zA-Z0-9_]", "", raw_summary.replace(" ", "_").lower())[:10]
    random_suffix = str(random.randint(1000, 9999))
    return f"{short_name}_{random_suffix}"

def save_to_file(filename: str, code: str) -> str:
    filepath = Path.cwd() / "solutions" / filename
    with open(filepath, "w") as f:
        f.write(code)
    print(f"✅ Saved to: {filepath}")
    return str(filepath)

# --- Main Agent Function ---
def run_code_agent(use_case: str, goals: str, max_iterations: int = 5) -> str:
    
    print("\n🎯 Use Case:")
    print(use_case)
    print("🎯 Goals:")
    print(goals)
    
    filename = create_short_filename(use_case)

    previous_code = ""
    feedback = ""
    for i in range(max_iterations):
        print(f"\n=== 🔁 Iteration {i + 1} of {max_iterations} ===")
        prompt = generate_prompt(use_case, goals, previous_code, feedback)
        
        print("🚧 Generating code...")
        code_response = llm_query(prompt)
        raw_code = code_response["code"].strip() if code_response["code"] else code_response["text"].strip() 
        code_output = code_response["output"]
        code_result = code_response["result"]
        code = clean_code_block(raw_code)
        print("\n🧾 Generated Code:\n" + "-" * 50 + f"\n{code}\n" + "-" * 50)
        if code_output:
            print("\n💻 Code Execution Output:\n" + "-" * 50 + f"\n{code_output}\n" + "-" * 50)

        code_filename = f"{filename}_v{i+1}.py"
        print(f"💾 Saving intermediate code to file {code_filename}")
        save_to_file(code_filename, code)

        print("\n📤 Submitting code for feedback review...")
        feedback = get_code_feedback(code, goals, code_output, code_result)
        feedback_text = feedback.strip()
        print("\n📥 Feedback Received:\n" + "-" * 50 + f"\n{feedback_text}\n" + "-" * 50)

        review_filename = f"{filename}_review_v{i+1}.txt"
        print(f"💾 Saving review to file {review_filename}")
        save_to_file(review_filename, feedback_text)

        if goals_met(feedback_text, goals):
            print("✅ LLM confirms goals are met. Stopping iteration.")
            break

        print("🛠️ Goals not fully met. Preparing for next iteration...")
        previous_code = code

    final_code = add_comment_header(code, use_case)
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

    use_case_input = load_file(f"tasks/{config_name}/hl_spec.md")
    goals_input = load_file(f"tasks/{config_name}/ac.md")
    run_code_agent(use_case_input, goals_input, max_iterations=25)
    