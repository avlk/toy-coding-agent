# Copyright (c) 2025 Andrey Volkov

# This work is a derivative work based on the original by Mahtab Syed.
# Original author copyright notice:
# MIT License
# Copyright (c) 2025 Mahtab Syed
# https://www.linkedin.com/in/mahtabsyed/

import os
import random
import re
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

def generate_prompt(use_case: str, goals: list[str], previous_code: str = "", feedback: str = "") -> str:
    print("📝 Constructing prompt for code generation...")
    base_prompt = f"""
        You are an AI coding agent. Your job is to write Python code based on the following use case:
        Use Case: {use_case}
        Your goals are:
        {chr(10).join(f"- {g.strip()}" for g in goals)}
    """
    if previous_code:
        print("🔄 Adding previous code to the prompt for refinement.")
        base_prompt += f"\nPreviously generated code:\n{previous_code}"
    if feedback:
        print("📋 Including feedback for revision.")
        base_prompt += f"\nFeedback on previous version:\n{feedback}\n"
    base_prompt += "\nPlease return only the revised Python code. Do not include comments or explanations outside the code."
    return base_prompt

def get_code_feedback(code: str, goals: list[str], code_execution: str, code_execution_result: str) -> str:
    print("🔍 Evaluating code against the goals...")
    feedback_prompt = f"""
You are a Python code reviewer. A code snippet is shown below. Based on the following goals:
{chr(10).join(f"- {g.strip()}" for g in goals)}
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

def goals_met(feedback_text: str, goals: list[str]) -> bool:
    """
    Uses the LLM to evaluate whether the goals have been met based on the feedback text.
    Returns True or False (parsed from LLM output).
    """
    review_prompt = f"""
        You are an AI reviewer.
        Here are the goals:
        {chr(10).join(f"- {g.strip()}" for g in goals)}
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
def run_code_agent(use_case: str, goals_input: str, max_iterations: int = 5) -> str:
    goals = [g.strip() for g in goals_input.split(",")]
    
    print(f"\n🎯 Use Case: {use_case}")
    print("🎯 Goals:")
    for g in goals:
        print(f" - {g}")
    
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

    # use_case_input = "Write code to find all positions of 8 Queens on a Chess board such that no two queens threaten each other. The program should print all unique solutions."
    # goals_input = "Code simple to understand, Functionally correct, Handles comprehensive edge cases, Computationally efficient, prints all unique solutions"
    # run_code_agent(use_case_input, goals_input)

    # use_case_input = "Write code to find BinaryGap of a given positive integer"
    # goals_input = "Code simple to understand, Functionally correct, Handles comprehensive edge cases, Takes positive integer input only, prints the results with few examples"
    # run_code_agent(use_case_input, goals_input)

    # use_case_input = """Write code to render an image of a ball with shadow into a text file of NxM characters with ASCII art. 
    #                     The ball has N/4 radius and is in the middle of a picture.
    #                     The ball is located on a horizontal plane with light source from the top left corner.
    #                     The ball has a shadow on the bottom right.
    #                     N and M are commandline arguments, but have default values of 80 and 120 respectively.
    #                     No colours are needed, just ASCII characters.
    #                     Take into account that the characters are taller than they are wide, the ratio is approximately 2:1 height to width.
    #                     The program should print the image."""
    # goals_input = "Code simple to understand, Functionally correct, Handles comprehensive edge cases, Rendered image is correct, Computationally efficient, prints the image"
    # run_code_agent(use_case_input, goals_input, max_iterations=15)

    # use_case_input = """Write code to render an image of 3d-looking bold "hpce" letters with a shadow into a text file of NxM characters with ASCII art. 
    #                     The letters height is 75 percent on N. The letters are in the middle of a picture.
    #                     The letters are slanted to the left with 10 degrees angle.
    #                     The letters are standing upright on a horizontal plane with the light source from the top left corner.
    #                     The letters have a shadow on the bottom right.
    #                     N and M are commandline arguments, but have default values of 60 and 120 respectively.
    #                     No colours are needed, just ASCII characters.
    #                     Take into account that the characters are taller than they are wide, the ratio is approximately 2:1 height to width.
    #                     The program should print the image."""
    # goals_input = "Code simple to understand, Functionally correct, Handles comprehensive edge cases, Rendered letters have correct case, clear outline and a shadow, Computationally efficient, prints the image"
    # run_code_agent(use_case_input, goals_input, max_iterations=15)

    use_case_input = """Write a C-like language interpreter. It shall have a parser, a type checker, and an code execution stages.
                        The interpreter shall be able to execute simple programs written in this language.
                        The interpreter shall have one main entry point function called interpreter_main(str), where str contains multi-line text of the program.
                        When the program is run from a command line, program code is provided to the interpreter as a text file whose path is passed as a commandline argument. 
                        The file is read and its content is executed with interpreter_main().
                        
                        The program also has embedded test mode.  When run with a "--test" flag, the program runs all tests defined in TEST_PROGRAMS.

                        The language shall support basic data types (integers, booleans, strings), control structures (if-else, for and while loops), and functions.
                        The interpreter shall be able to handle syntax errors and runtime errors gracefully.
                        The I/O in this language is through stdin and stdout only and there is a native print() command to print whatever is passed into it and 
                        read_int(), read_bool() and read_str() statements to read user input.

                        A test set of programs shall be provided to validate the interpreter's functionality as a list of dictionaries of the following structure:
                        TEST_PROGRAMS = [
                            { "code": "<program code as string>", 
                            "description": "<short description of what the program does>", 
                            "expected_output": "<expected output when the program is run>",
                            "inputs": [<list of bool, int and string inputs for the program>]
                            },
                            ...
                        ]
                        In a test mode, program code provided by "code" is passed as a string input to the interpreter, 
                        the output is is accumulated into "output" line-by-line and then compared against "expected_output".
                        "inputs" are mocking any real read_int(), read_bool() and read_str() calls in the program.
                        When running tests, for each test the status PASS or FAIL shall be recorded along with any error messages for failed tests. 
                        At the end of test run, total number of tests and number of passed tests shall be printed.
                        A test suite shall include, among others, tests for: recursion, complex expressions inside function call parameters and control structures.
                        The number of test programs shall be kept reasonable (preferably below 100) to not overflow the LLM context window.
                        Do minimization of the test program number by combining multiple tests into one where possible.

                        An embedded markdown documentation of the language syntax and features shall be provided as a multi-line string variable called LANGUAGE_SPECIFICATION.
                        When run from command line with "--syntax" flag, the program shall print this documentation to stdout and exit.
                        
                        Make sure that the interpreter compiles and runs the test programs by using the code_execution tool before submitting the result.
                        """
    goals_input = "The interpreter is functionally correct, handles comprehensive edge cases, Functionally complete, Has test programs for all language features, executes all test programs correctly, Has embedded markdown documentation of the language syntax and features"
    run_code_agent(use_case_input, goals_input, max_iterations=25)
    