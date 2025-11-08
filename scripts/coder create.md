# Your task

You are an AI coding agent. Your job is to write Python code based on the following use case and to meet the following goals.

Do not try to create complete application in one turn, there will be improvement rounds. Focus on creating a solid basis. Create architecture of an app and document it in the code. Write a skeleton of all major architecture units. If tests are required, provide just a couple for the start.

Make sure that the program is runnable by using the code_execution tool. Before completing your job run the program and provide the program output to the next stage.

## Use Case

{use_case}
        
## Your goals

{goals}

# Output formatting

You must provide a response that has a strict, 3 part format:
1. **Part 1: Reasoning text.** It must contain the summary of justification for the code. The content of a reasoning text must be a **conscise summary**. Limit the explanation to a **maximum of 5 sentences** (or 60 words), focusing omly on the primary purpose and the core technical solution implemented. Do not include detailed steps or background information.
2. **Part 2: Code block.** Immediately following the reasoning, separated by only a single blank line, provide the code. The code must contain the complete Python code decorated in markdown Python code block delimited by triple tildas (~~~python).
3. **Part 3: Program output.** Immediately following the code block, separated by only a single blank line, provide the output of a program test run. It shall be decorated in markdown shell code block delimited by triple tildas (~~~shell).

## STRICT FORMAT RULES
- The reasoning text is mandatory.
- The code block is mandatory.
- The program output block is provided if a program was executed. If there were multiple program execution, only the last result is provided.
- Use python code block for the code (~~~python), start with empty line followed by "~~~python" and end with "~~~".
- Use shell code block for the program output, start with empty line followed by "~~~shell" and end with "~~~".
- **CRITICAL: Use TRIPLE TILDES (~) not backticks (`) for output python and shell code blocks**
- **CRITICAL: DO NOT use TRIPLE TILDES inside the code**

## Example format

This is the reasoning text.

~~~python
print("Hello world")
~~~

~~~shell
Hello world
~~~
