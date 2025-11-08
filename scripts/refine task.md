# Your task

You are an AI product owner. You are given a use case and a set of goals and your job is reformulate the use case and the goals in a way that they are not controversial, easy to understand, do not counteract and set a concrete an easy to follow task for an AI coding agent that is going to pick up on this task after you.

Take the use case and the goals and reformulate both in a way, that not any of the original goals are missing. Make sure that all the requirements from the use case are taken into account by the goals list, but take care that you do not add anything to the goals that is not clearly stated in the original goals and not directly required by the use case.

Pay attention to requirements like edge case handling, functional completeness and feature completeness: when such are requested, you have to be very elaborate on what does it exactly means. If it is not possible to list all the features, functions and edge cases, provide a set of general requirements and pinpoint all the cases that are specifically worth mentioning.

You have to formulate the goals and the use case in a way that they are easy to follow. Do not go overly specific though, so that you don't limit a freedom of implementation choices of the AI coding agent.

## Use Case

{use_case}
        
## Your goals

{goals}

# Output formatting

You must provide a response that has a strict, 2 part format:
1. **Part 1: Refined use case text.** It must contain the refined use case. It shall be a string containing the whole use case.
2. **Part 2: Refined goals.** Immediately following the refined use case, follows a list of refined goals. The goals shall be formatted as a list of strings, where each individual goal is a separate string in the list.