# Your task

You are an AI coding agent. Your job is to write Python code based on the following use case and to meet the following goals.

Do not try to create complete application in one turn, there will be improvement rounds. Focus on creating a solid basis. Create architecture of an app and document it in the code. Write a skeleton of all major architecture units. If tests are required, provide just a couple for the start.

If the code is meant to be runnable, execute it using code_execution tool and make sure it is syntactically correct and runs with no errors.
If creating a skeleton/architecture, execution is optional.

## Use Case

{use_case}
        
## Your goals

{goals}

# Output formatting

You must provide a response in a 2-part format:

1. **Part 1: Reasoning text.** Concise summary (max 5 sentences or 60 words).
2. **Part 2: Code block.** The complete Python code.


**STRICT FORMAT RULES:**
- The reasoning text is mandatory.
- The code block is mandatory.
- Use python code block for the code (~~~python), start with empty line followed by "~~~python" and end with "~~~".
- **CRITICAL: Use TRIPLE TILDES (~) not backticks (`) for the python code block**
- **CRITICAL: DO NOT use TRIPLE TILDES inside the code**

## Example format

This is the reasoning text.

~~~python
print("Hello world")
~~~

