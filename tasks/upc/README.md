# UPC Code Generator

This is a low-creativity task, but it is relatively complex.
The main challenge is that it requires fetching external sources,
working with table data, and implementing precise tests.

The agent must design a program to print UPC barcodes that are
readable by a smartphone. Since there is no direct way to test
barcode readability, the agent must rely on research about UPC/Code 128
standards and implement precise unit tests for both encoding and decoding.

It is essential to provide external URLs for this task. The researcher
component will convert these into a prepared research summary with data
tables in Python format. Without this research, the model might invent
its own Code 128 encodings, resulting in output that is internally
consistent but not actually scannable by a smartphone.

This task is solvable by the gemini-2.5-flash model in 4–6 iterations
with the `--no-diffs` flag, although not always on the first try.
Without the `--no-diffs` flag, it may take 10–15 iterations to complete.

The coder, when using gemini-2.5-flash, operates at its limits in this
task: the input data and context are so large and diverse that it can
lose focus and fail to follow instructions. It often will not fetch the
provided URLs, even if equipped with the appropriate tool and prompt,
because it cannot determine the most important step. The research step
helps mitigate this issue. The researcher has a single job: to summarize
data fetched from URLs and provide the result. This result is then fed
into both the coder and reviewer contexts. It is important to provide
the same research to the reviewer; otherwise, the coder will use real
data (encoding tables), while the reviewer may hallucinate or assume it
knows the data and prompt the coder to change its mappings.