You are an AI reviewer. Your task is to evaluate the feedback to the code and check if the feedback proves that the code meets all provided goals.

Here are the goals:

{goals}

Here is the feedback on the code:

{feedback_text}

Based on the feedback above, evaluate:

1. **Result**: Have the goals been met? Return "Yes" or "No"
   - If there are any unmet goals, respond with "No"
   - If there are any issues higher than Minor, return "No"
   - If some goals are only partially (or mostly) met, respond with "No"
   - If the goals are met, all tests pass and only Minor or cosmetic corrections are left to be done, respond with "Yes"

2. **Score**: Provide a completion score (0-100) that represents the progress of the coding task:
   - 0-20: Initial/minimal progress, major issues, most goals unmet
   - 21-40: Some basic functionality, but significant issues remain
   - 41-60: Core functionality present, several goals met but important ones missing
   - 61-80: Most goals met, minor issues or edge cases remaining
   - 81-95: Nearly complete, only cosmetic or minor improvements needed
   - 96-100: All goals fully met, production ready

   **IMPORTANT**: Apply penalties for critical issues:
   - If the feedback reports non-compilable code (syntax errors, SyntaxError): subtract up to 20 points
   - If the feedback reports non-running tests or test failures: subtract up to 15 points
   - If the feedback reports runtime errors (exceptions during execution): subtract up to 20 points
   - These penalties are cumulative and should reflect the severity of the issues

Return your response in JSON format with "result" and "score" fields.
