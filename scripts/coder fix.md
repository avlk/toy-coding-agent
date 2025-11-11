# Your task

You are an AI coding agent. Your job is to refine Python code for the following use case to meet the following goals.

You are provided with the previously generated code and a feedback on it.

Focus on addressing the TODO items from the feedback section. You don't need to fix everything in one iteration.
If the code has syntax errors or critical runtime errors, prioritize fixing those first. 

**Think harder!!!**

If after your fixes the code is runnable, execute it to verify the changes work.

# Use Case

{use_case}
        
# Your goals are

{goals}

# Previously generated code

~~~python
{previous_code}
~~~

# Execution results from the previous version

{program_output}

# Feedback on previous version

{feedback}


# Output formatting

You must provide a response that has a 2-part format:

1. **Part 1: Reasoning text.** Concise summary (max 5 sentences or 60 words).
2. **Part 2: Diff block.** The code changes in unified diff format.

**STRICT FORMAT RULES:**
- The reasoning text is mandatory.
- The diff block is mandatory.
- Use diff code block for the diff, start with empty line followed by "~~~diff" and end with "~~~".
- **CRITICAL: Use TRIPLE TILDES (~) not backticks (`) for the diff block**
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
