# Your task

You are an AI coding agent. Your job is to refine Python code for the following use case to meet the following goals.

You are provided with the previously generated code and a feedback on it.

Focus on addressing the TODO items from the feedback section. You don't need to fix everything in one iteration.
If the code has syntax errors or critical runtime errors, prioritize fixing those first.

If after your fixes the code is runnable, execute it to verify the changes work.
If the code is not yet ready to run (e.g., still needs more implementation), that's fine - just provide the diff without output.

# Use Case

{use_case}
        
# Your goals are

{goals}

# Previously generated code

~~~python
{previous_code}
~~~

# Execution errors from the previous version

{error_output}

# Feedback on previous version

{feedback}

{execution_warning}

# Output formatting

You must provide a response that has either a 2-part or 3-part format:

**2-part format (when code is not yet runnable):**
1. **Part 1: Reasoning text.** Concise summary (max 5 sentences or 60 words).
2. **Part 2: Diff block.** The code changes in unified diff format.

**3-part format (when code is runnable and executed):**
1. **Part 1: Reasoning text.** Concise summary (max 5 sentences or 60 words).
2. **Part 2: Diff block.** The code changes in unified diff format.
3. **Part 3: Program output.** ONLY if you actually executed the code. Real execution results, not predictions.

**STRICT FORMAT RULES:**
- The reasoning text is mandatory.
- The diff block is mandatory.
- The program output block is provided if a program was executed. If there were multiple program executions, only the last result is provided.
- Use diff code block for the diff, start with empty line followed by "~~~diff" and end with "~~~".
- Use shell code block for the program output, start with empty line followed by "~~~shell" and end with "~~~".
- **CRITICAL: Use TRIPLE TILDES (~) not backticks (`) for output diff and shell code blocks**
- **CRITICAL: DO NOT use TRIPLE TILDES inside the code**

## Example format

This is the reasoning text.

~~~diff
--- a/main.py
+++ b/main.py
@@ ... @@
 def hello():
-    print("old")
+    print("new")
     return True
~~~

~~~shell
Hello world
~~~

## CODE EXECUTION REQUIREMENT

**Execute code ONLY if it's ready to run:**
- If your changes fix critical errors and the code should now run: Execute it and provide the output.
- If the code still needs more work or is not yet complete: Omit the program output section.

**NEVER provide fake or simulated output.**
If you didn't actually execute the code using code_execution tool, do not include a ~~~shell block.
It's better to provide no output than fake output.
