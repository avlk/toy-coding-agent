# Your task

You are an AI coding agent. Your job is to refine Python code for the following use case to meet the following goals.
The code you are refining has to be a single file of Python code.

You are provided with the previously generated code and a feedback on it.

Address the TODO items from the feedback section.
If the code has syntax errors or critical runtime errors, prioritize fixing those first. 
If the code has placeholder items to be filled with the real code, do fill such placeholders.

When there are URL's provided for context, you can fetch them with a url_context tool to get additional knowledge.

Do run the code after your fixes using the code_execution tool and make sure the code is syntactically correct and runnable.

# Use Case

{use_case}
        
## Technical Research

{research_summary}

# Your goals are

{goals}

# Previously generated code

~~~python
{code}
~~~

# Execution results from the previous version

{output}

# Feedback on previous version

{feedback}

# Output formatting

You must provide a response that has a 2-part format:

1. **Part 1: Reasoning text.** Concise summary (max 5 sentences or 60 words).
?a 2. **Part 2: Diff block.** The code changes in unified diff format.
?b 2. **Part 2: Code block.** The complete Python code.

**STRICT FORMAT RULES:**
- The reasoning text is mandatory.
?a - The diff block is mandatory.
?a - Use diff code block for the diff, start with empty line followed by "~~~diff" and end with "~~~".
?a - **CRITICAL: Use TRIPLE TILDES (~) not backticks (`) for the diff block**
?b - The code block is mandatory.
?b - Use python code block for the code (~~~python), start with empty line followed by "~~~python" and end with "~~~".
?b - **CRITICAL: Use TRIPLE TILDES (~) not backticks (`) for the python code block**
- **CRITICAL: DO NOT use TRIPLE TILDES inside the code**

## Example format

This is the reasoning text.

?a ~~~diff
?a --- a/main.py
?a +++ b/main.py
?a @@ ... @@
?a  def hello():
?a -    print("old")
?a +    print("new")
?a      return True
?a ~~~
?b ~~~python
?b print("Hello world")
?b ~~~