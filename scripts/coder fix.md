# Your task

You are an AI coding agent. Your job is to refine Python code for the following use case to meet the following goals.

You are provided with the previously generated code and a feedback on it. You do not need to fix everything in one turn, focus on items of the TODO list provided in the feedback section.

# Use Case

{use_case}
        
# Your goals are

{goals}

# Previously generated code

{previous_code}

# Feedback on previous version

{feedback}

# Output formatting

You must provide a response that has a strict, 3 part format:
1. **Part 1: Reasoning text.** It must contain the summary of justification for the code. The content of a reasoning text must be a **conscise summary**. Limit the explanation to a **maximum of 5 sentences** (or 60 words), focusing omly on the primary purpose and the core technical solution implemented. Do not include detailed steps or background information.
2. **Part 2: Diff block.** Immediately following the reasoning, separated by only a single blank line, provide the patch (unified diff format) to the revised Python code, decorated in markdown diff code block delimited by triple tildas (~~~diff).
3. **Part 3: Program output.** Immediately following the code block, separated by only a single blank line, provide the output of a program test run. It shall be decorated in markdown shell code block delimited by triple tildas (~~~shell).

**STRICT FORMAT RULES:**
- The reasoning text is mandatory.
- The diff block is mandatory.
- The program output block is provided if a program was executed. If there were multiple program execution, only the last result is provided.
- Use diff code block for the diff, start with empty line followed by "~~~diff" and end with "~~~".
- Use shell code block for the program output, start with empty line followed by "~~~shell" and end with "~~~".
- **CRITICAL: Use TRIPLE TILDES (~) not backticks (`) for output diff and shell code blocks**
- **CRITICAL: DO NOT use TRIPLE TILDES inside the code**

## Example format

This is the reasoning text.

~~~diff
--- a/main.py
+++ b/main.py
@@ -140,8 +140,7 @@
...
~~~

~~~shell
Hello world
~~~
