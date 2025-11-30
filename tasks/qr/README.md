# QR Code Generator

This is a low-creativity task, but it is relatively complex for the agentic flow
we have in this application.

The agent must design a program to print QR codes that are readable by a smartphone.
It shall not use any external libraries to encode a QR code.

It is essential to provide external URLs for this task, otherwise the model is
likely to hallucinate parts of Galois field maths and polynomials, leading to
a fake solution. The researcher component will convert these into a prepared
research summary with data tables in Python format. The coder and the reviewer
both receive this review, so that they are on the same page.

In general, there is no direct way to test the QR readability,
and there are several ways to test it, with different levels of confidence:

- Rely on research data and create a compliant decoder - low confidence,
  as the decoder can be incorrectly designed.
- Use a golden sample (pre-encoded QR matrics) to test the encoder - medium
  confidence and error-prone. There are multiple ways to encode a test into
  a QR due to different masks. The way the code selects a mask shall be 100%
  compliant with the standard. It also only tests one encoding.
- Rely on research data and create a compliant decoder, then use a golden
  sample to test the decoder - also medium confidence, as we only test one case.
- Use 3rd-party libraries to decode a multitude of QR codes generated with
  the encoder - high confidence, but requires using extra libraries.

The last one seems to break the rule of not using 3rd-party libraries and
in general seems to make the agent's task much easier. However, it is not the
case: The agent is using external libraries to check it's own implementation,
and it's the approach many of us would use to check our own code.
This was the approach that the LLM tried to use in one of the runs and I found
out that it is actually better to allow it to do so, rather then insist on the
strict rules. If we want models solve real world tasks, we shall allow for a
real world approach, rather than a "whiteboard job interview-style programming".

As it is beneficial to allow the model to use some external libraries in the code,
and here `numpy` and `opencv-python` are allowed. Doing so puts the coder and
the reviewer onto the same playing field: the libraries are available to the
coder as part of a `code_execution` tool; if they are not available for local
code execution, the reviewer will constantly receive results differing from
the coder's point of view. As a result, even a correct encoder implementation
won't pass the tests and the `coding-agent` will go in loops.

This task is solvable by the gemini-3-pro-preview model in 4–8 iterations
with the `--no-diffs` flag. It may not always complete on the first try.

It is also solvable with the gemini-2.5-flash, but with a much lower
success rate and consuming much more tokens. It showcases that using
a more expensive Gemini 3 is actually cheaper than using a simpler, cheaper model.
