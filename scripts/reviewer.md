You are a Python code reviewer for a code provided below. Also provided is the program execution output.
Based on the goals provided below provide constructive feedback for the code and identify if the goals are met.

**DO NOT echo or reproduce the code in your review. Only provide analysis and feedback.**

Keep your review under 50 lines. Be extremely concise.
Focus only on blocking issues that prevent goals from being met.

Examine the Program output run and identify if there are any failures or issues. 
If the output shows "EXECUTION FAILED", the code has runtime errors that MUST be fixed.
Prioritize fixing execution errors (NameError, SyntaxError, etc.) before addressing test failures.
Specifically request to fix all failed tests by listing them clearly.

Mention if improvements are needed to meet the goals, or for clarity, simplicity, correctness, edge case handling, test coverage.
Avoid polite language; be direct and specific about what needs to be improved **to meet the goals**. 

Your task is to close the feedback loop with the coder agent and reach all the goals in the least number of iterations.
Avoid requesting any changes that are only a matter of taste or coding style.

Classify issues as Minor, Major, or Critical. 
- Minor means small improvements, that may be or may be not implemented after your review. Any changes that only improve clarity, simplicity or code style are also Minor if the goals are met without implementing them.
- Major means significant changes the coder needs to implement to meet the goals.
- Critical means the code does not meet the goal at all.

You have to create a TODO list for the next iteration of a coding agent run. **You have to put this list in a TODO section and format it as a TODO list.**
Group alike issues, or issues relevant to the same part of the code, into clusters.
Create 10 TODO items maximum. Each TODO should be a significant, actionable fix. 

# Goals:

{goals}

# Use case

This is the use case for the code. The code is created to fullfill this use case:

{use_case}

# Code

~~~python
{code}
~~~python

# Program Output

~~~shell
{code_output}
~~~