# Toy Coding Agent

This is a toy coding agent, yet capable of solving complex tasks. It autonomously generates, tests, and iteratively refines Python code to meet specified requirements. The agent uses Google's Gemini models in a multi-stage workflow with feedback loops, combining multiple AI design patterns to achieve reliable code generation.

It evolved from demo code for Chapter 11, "Goal Setting and Monitoring" of "Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems" book by [Antonio Gulli](https://www.linkedin.com/in/searchguy/).

The code for the chapter was written by [Mahtab Syed](https://www.linkedin.com/in/mahtabsyed/) and demonstrated a simple agent with a feedback loop, involving Coder and Reviewer sub-agents, able to complete simple coding tasks.

I was curious to push this simple pattern to its limits. This project is still an educative example, but its size is beyond that of a book demo code.

In this file, you will find:

- Overview of agent functioning
- Setup and running
- Available coding tasks
- Architecture of the main execution loop
- Explanations for each execution stage
- Cross-references to the Agentic Design Patterns used in the code

## License

MIT License  
Copyright (c) 2025 Andrey Volkov  
[https://www.linkedin.com/in/andrey-volkov-gri/](https://www.linkedin.com/in/andrey-volkov-gri/)  
This work is a derivative work based on the original by Mahtab Syed.

**Original author copyright notice:**  
MIT License  
Copyright (c) 2025 Mahtab Syed  
[https://www.linkedin.com/in/mahtabsyed/](https://www.linkedin.com/in/mahtabsyed/)

## Acknowledgments

This work would not have been possible without:

- The book "Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems" by [Antonio Gulli](https://www.linkedin.com/in/searchguy/), available on [Springer](https://tidd.ly/47Q27j4), [Amazon](https://tidd.ly/3WZC9n7)
- Demonstration code for Chapter 11 of this book written by [Mahtab Syed](https://www.linkedin.com/in/mahtabsyed/)
- Google Gemini free tier access

## Overview

This coding agent implements an iterative development workflow where AI models collaborate to:

1. **Refine** the problem statement and acceptance criteria
2. **Research** external documentation and resources
3. **Generate** Python code that meets the requirements
4. **Execute** the code in a secure sandbox environment
5. **Review** the output against goals
6. **Iterate** until the solution is complete or the maximum number of iterations is reached

The agent is capable of handling complex programming tasks including algorithm implementation, data structure manipulation, protocol encoders/decoders, and more.

## Features

- 🔄 **Iterative refinement** with automatic feedback loops
- 🔒 **Secure sandboxed execution** (Firejail, Docker, Bubblewrap)
- 🔍 **Automated research** from external URLs and documentation
- 🧪 **Syntax error detection and auto-repair**
- 📊 **Progress tracking** with automatic rollback on stagnation
- 🎯 **Goal-based evaluation** with scoring
- 📝 **Unified diff patching** for efficient code modifications
- 📦 **Python package support** with virtual environments
- 🔢 **Token usage tracking** and cost monitoring

## Installation

### Prerequisites

- Python 3.8+
- Google Gemini API key
- (Optional) Sandbox tools: Firejail, Docker, or Bubblewrap

### Setup

1. **Clone the repository:**

```bash
git clone <repository-url>
cd coding-agent
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up your Gemini API key:**

If you don't have an API key, register for one. Google provides a free tier for LLM experimenters.  
There is also a $300 sign-up credit you can use to test any model in Tier 1.

```bash
export GEMINI_API_KEY="your-api-key-here"
```

4. **Install sandbox tools (optional but recommended):**

See **[README_SANDBOX.md](README_SANDBOX.md)** for detailed documentation and installation instructions.

## Usage

### Basic Command

```bash
python coding_agent.py <task-name>
```

Where `<task-name>` is a directory in the `tasks/` folder containing task configuration.

### Command-Line Options

- `--refine-goals` / `--no-refine-goals`: Enable/disable goal refinement (default: enabled)
- `--diffs` / `--no-diffs`: Use unified diffs for code modifications (default: enabled)
- `--reset N`: Reset to the last successful iteration after N unsuccessful attempts (default: 3)
- `--no-reset`: Disable automatic rollback on stagnation

### Examples

```bash
# Run the 8-queens task with default settings
python coding_agent.py 8-queens

# Run QR code generator without goal refinement
python coding_agent.py 3d-ball --no-refine-goals

# Run with no automatic resets
python coding_agent.py upc --no-reset 

# Run without using diffs
python coding_agent.py qr --no-diffs
```

## Available Tasks

The `tasks/` directory contains several pre-configured tasks:

### 1. **8-queens** (Difficulty: Easiest)

Solve the classic 8 Queens problem and print all solutions. A simple algorithmic task suitable for testing the basic workflow.  
The model does not require any external sources to complete the task as it already knows about the problem from its learning set.  
It may already have seen some solutions, and it can, of course, code.

### 2. **3d-ball** (Difficulty: Easy)

Create ASCII art animation of a 3D sphere throwing a shadow onto a plane.  
While the model is aware of geometric calculations and basic visualization options from its training data,  
it takes some effort to assess if the picture is rendered correctly.

### 3. **c-interpreter** (Difficulty: Medium)

Design a C-like language and implement its interpreter along with the test suite.  
It tests the model's ability to design a language, plan implementation steps, create a set of tests, and fix the code.  
The code does not come out perfect or even feature-complete after the first run, and it takes significant effort to get it done.  
While it was expected to be a hard task, it is not that hard actually, as the model does not need any external context for task completion:  
it knows plenty about programming languages, testing, reviewing code, and it can code very well.

### 4. **upc** (Difficulty: Hard)

Barcode generator and validator. A Code-128 barcode generator is not the hardest thing to do. What it does is basically just take a table mapping input characters to the bar sequences, map input data to the output sequence, and print it. Surprisingly, it is a hard task for an LLM, as it does not know any of these mappings by heart. To make the model use the right mapping, resource URLs are provided, which are parsed by a Researcher sub-agent and fed into the prompt. The data from the researcher fills up the context window and makes the model think about it, summarize the data, which generally reduces the number of tokens and context left for thinking and writing correct code.

### 5. **qr** (Difficulty: Hardest)

Generate QR codes that are readable by smartphones without using external QR encoding libraries. Requires research from external URLs to understand the QR code standard.

While being of the same type as the **upc** task, it brings much more complexity:

1) The codes use GF(2^8) math, and the model is generally not good at math, and it is much less good at Galois field calculations. GF(2^8) math can't be quickly proven by its internal Python interpreter. It would be fair to say that the model knows about Galois fields, of course, it just misses some details here and there.  
2) The code is two-dimensional, and code point locations are much easier to show in a picture than to explain with words, but the model only receives words. It's really, really hard to understand the logic behind QR code pixel placement by only reading words.  
3) The QR code uses Reed-Solomon error correction, which is another layer of mathematical complexity for the model.  
4) The model has to select and use some non-trivial way to test the code readability.  

Overall, after the model processes and understands everything it needs to complete the coding round, it has not too many tokens left for thinking and tool use. The Gemini-2.5-flash model is usually quite quickly overwhelmed with the complexity, fails to run the code execution tool to proofread its code, generates faulty diffs, and often repeats its previous errors. It is not impossible, but hard to reach the goals when not using Gemini-3-pro for this task.

## Task Configuration

Each task is defined in `tasks/<task-name>/` with the following structure:

```shell
tasks/
  <task-name>/
    config.json       # Task configuration
    hl_spec.md        # High-level specification (use case)
    ac.md             # Acceptance criteria (goals)
    README.md         # Task documentation
```

### config.json Format

```json
{
  "coder_model": "gemini-2.5-pro",
  "reviewer_model": "gemini-2.5-pro",
  "utility_model": "gemini-2.5-flash-lite",
  "max_rounds": 15,
  "basename": "solution",
  "sandbox_method": "auto",
  "commandline_args": "",
  "urls": [
    "https://example.com/spec.html"
  ],
  "python_packages": ["numpy", "opencv-python"]
}
```

**Configuration Options:**

- `coder_model`: Model for code generation
- `reviewer_model`: Model for code review and feedback
- `utility_model`: Model for utility tasks (goal checking, research)
- `max_rounds`: Maximum iteration count
- `basename`: Prefix for generated solution files
- `sandbox_method`: Execution environment (auto, firejail, docker, bubblewrap, subprocess)
- `commandline_args`: Arguments to pass when executing the generated code
- `urls`: External documentation URLs for research phase (optional)
- `python_packages`: Extra packages to install in sandbox venv to make local execution successful (optional). The code_execution tool of the model has a limited set of packages in its cloud shell. The model may decide to use any of those if not limited by the prompt. Ensure that your local execution environment has the required packages installed to avoid failures during the `import` directive.

A list of models: gemini-2.5-flash-lite, gemini-2.5-flash, gemini-2.5-pro, gemini-3-pro-preview.

A list of packages the code_exection tool has access to: attrs, chess, contourpy, fpdf, geopandas, imageio, jinja2, joblib, jsonschema, jsonschema-specifications, lxml, matplotlib, mpmath, numpy, opencv-python, openpyxl, packaging, pandas, pillow, protobuf, pylatex, pyparsing, PyPDF2, python-dateutil, python-docx, python-pptx, reportlab, scikit-learn, scipy, seaborn, six, striprtf, sympy, tabulate, tensorflow,toolz, xlrd.

## Architecture

### Main Execution Cycle

The agent employs a sophisticated iterative workflow that integrates multiple agentic AI patterns:

```txt
┌─────────────────────────────────────────────────────────────┐
│                    INITIALIZATION PHASE                     │
├─────────────────────────────────────────────────────────────┤
│  1. Load task configuration (config.json)                   │
│  2. Read use case (hl_spec.md) and goals (ac.md)            │
│  3. [Optional] Refine goals using LLM                       │
│  4. [Optional] Research external URLs                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    ITERATION LOOP (1..N)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌────────────────────────────────────────────────────┐    │
│   │  1. CODE GENERATION (Coder Agent)                  │    │
│   │     - First iteration: Create initial solution     │    │
│   │     - Subsequent: Apply fixes based on feedback    │    │
│   │     - Uses unified diffs for efficient updates     │    │
│   │     - Quality gate: restart iteration if model     │    │
│   │       misbehaved                                   │    │
│   └────────────────────────────────────────────────────┘    │
│                          ↓                                  │
│   ┌────────────────────────────────────────────────────┐    │
│   │  2. CODE EXECUTION (Sandbox)                       │    │
│   │     - Run in secure environment (firejail/docker)  │    │
│   │     - Capture stdout, stderr, exit code            │    │
│   │     - Detect syntax/runtime errors                 │    │
│   └────────────────────────────────────────────────────┘    │
│                          ↓                                  │
│   ┌────────────────────────────────────────────────────┐    │
│   │  3. SYNTAX ERROR REPAIR (Optional)                 │    │
│   │     - Runs on SyntaxError/IndentationError         │    │
│   │     - Lightweight task with high success chances   │    │
│   │     - Generate and apply fix patches               │    │
│   │     - Re-execute corrected code                    │    │
│   └────────────────────────────────────────────────────┘    │
│                         ↓                                   │
│   ┌────────────────────────────────────────────────────┐    │
│   │  4. CODE REVIEW (Reviewer Agent)                   │    │
│   │     - Evaluate against goals                       │    │
│   │     - Compare with previous feedback               │    │
│   │     - Generate detailed improvement suggestions    │    │
│   └────────────────────────────────────────────────────┘    │
│                         ↓                                   │
│   ┌────────────────────────────────────────────────────┐    │
│   │  5. GOAL EVALUATION (Utility Agent)                │    │
│   │     - Score solution (0-100)                       │    │
│   │     - Determine if goals are met (Yes/No)          │    │
│   └────────────────────────────────────────────────────┘    │
│                         ↓                                   │
│   ┌────────────────────────────────────────────────────┐    │
│   │  6. PROGRESS CHECK                                 │    │
│   │     - Track score progression                      │    │
│   │     - Detect stagnation (no progress)              │    │
│   │     - Rollback to last best iteration if stuck     │    │
│   └────────────────────────────────────────────────────┘    │
│                         ↓                                   │
│              Goals met OR max iterations?                   │
│                    Yes ↓    No ↑                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   FINALIZATION PHASE                        │
├─────────────────────────────────────────────────────────────┤
│  1. Format final code with metadata comments                │
│  2. Save solution to solutions/ directory                   │
│  3. Print token usage summary                               │
└─────────────────────────────────────────────────────────────┘
```

### Main execution steps

#### Refiner

Task definition is composed of a high-level spec (tasks/\*/hl_spec.md) as a freeform text and acceptance criteria (tasks/*/ac.md) as a list. This approach is inherited from the book example code. This differentiation defines a borderline between what we *would like* to have and what we *accept* as a valid solution. While both parts are equally important for the coder, meeting acceptance criteria is the main evaluation parameter for the reviewer.

The `coding-agent` refines the spec and the AC by rethinking and re-generating them. It helps to sort out the following:

- In cases where the acceptance criteria do not align with the specification.
- In cases where we see contradictions in what we ask from the agent.
- In cases where we miss important assumptions.
- In cases where we think we require something from the model but we actually don't.

It works as an Occam's razor.

It is worth looking into the refined goals and spec files while the agent is running  (`{name}_refined_use_case.md`, `{name}_refined_goals.md`) to detect if some of your initial assumptions were so subtly stated that they were completely omitted by the refiner.

>**Example of a missing assumption**: We want the model to write a simple calculator. In the AC we require that the calculator performs for arithmetic operations and is fully functional. And assumption added in the refinement state may be: the program has an interactive CLI interface. Without this assumption the coder and the reviewer may have different views on what interface the calculator shall have.

The Refiner works as a perfect manager in contract development, removing everything that is not directly required by the contract. If you think that the password manager it designs will by default comply with GDPR but you don't state it explicitly, the Refiner may completely omit this requirement.

In some cases you are loading too much context into the spec and the Refiner may not like it. To push it through, run the agent with `--no-refine-goals`.

Check out the prompt in `scripts/refine task.md`

#### Researcher

In come cases the model doesn't have enough context to complete the task. This is the case with `upc` and `qr` tasks, where the model has an idea about bar codes, QR codes, and some math behind it, but it misses some constant, tabular data and can't be sure about some things.

With no external context the model would hallucinate all the missing data and will either fail, or create an isolated solution that only passes its own tests but not work with any real world scenarios.

The Researcher stage acts when some URLs are provided in the task's `config.json` file. It will summarize the text from these URLs and process the data provided in the tables and the text.

The way data processing is done is crucial: by default, the model may shorten the tables it finds in the pages, putting ellipsis into the output table. We ask it not to do so.

Then, the model tends to provide the table with all it's formatting. Each formatting character is a token and passing this result later into the coder will make it re-think the data all over again and will fill it's context window. As a solution, we ask the Researcher to provide all necessary data as Python language structures. With some luck these structures are quite well defined to be directly used in the code.

Quite often the coder will only need a subset of data we receive from the URLs. To not overload the coder's context, we provide the Researcher with the use case and the goals and ask it to only output relevant data.

> **Note**: It is worth mentioning, that while the Researcher is promptly asked to summarize all the documents and output the summary, it often fails to summarize the findings from multiple documents and output just **one** summary. If `N >>> 2` documents are provided, and the documents are big, the Researcher will likely provide N summaries instead of providing just one. This happens also in cases the documents tell basically tell the same thing. The model is overwhelmed and misses the last summarization stage. It is therefore better to provide just a few docs and expect that the model's pre-trained knowledge would bridge the gap if something is missing.

Check out the prompt in `scripts/research.md`

#### Coder - Initial run

The Coder sub-agent is responsible for writing and refining the code.

When there is no prior code, its prompt is composed of: a system prompt, the use case, the goals, the research data. It uses the system prompt from `scripts/coder create.md`. It shall output some reasoning and a code block.

The reasoning is commonly said to be important in the prompt to make the model think deeper, and it seems to really work. What it also does is  channeling model's thoughts into some output stream: rather then placing the thoughts into some random place, it knows where and how to deliver it.

> The output code block shall be formatted with triple-tilde markdown code block. It is important, as the model tends to use triple-backticks markdown code blocks in the python code it generates

The initial `scripts/coder create.md` prompt asks not to complete the code, but rather create a skeleton of an app. There are *pro* and *contra* to this approach.

- If the model is asked to complete the code in one run, it may very well do it for simpler tasks, but it can also hit the limit of its capabilities and only output some starting part of the code. If it does so, it fails to communicate its architecture idea and assumptions to a next iteration, and the next run of the code agent will have to create some architecture assumptions again. Not only we make the model think more at the later stage, we also lose some of its thinking from the first iteration.
- The downside of this approach is that the model is generally weaker at creating changes to the code at a later stage: it can generate a 500 LoC python code in the first run, but will only output some patches of 1-50 LoC in each run later. If the task is huge, asking for just an architecture in the first run leaves too much to be done by subsequent runs.

#### Coder - Subsequent runs

When there is already code and review of the previous iteration, the Coder sub-agent is run with `scripts/coder fix.md` system prompt. Its prompt is composed of the system prompt, the use case, the goals, the research data, the previously generated code, code execution output, and review results.

The Coder shall output some reasoning and a code/diff block. Normally, the agent asks the model to generate unified diffs, unless `--no-diffs` parameter is supplied in the command line. A simple pre-processing is performed to the prompt to dynamically modify it for diff or full code output: lines starting with `?a` are only copied into the prompt for the diff variant, and lines starting with `?b` are only copied for the full code variant (prefixes are of course removed).

#### Coder - Multipart prompt

Having so many data in the prompt is difficult for the model: it is hard for the model to follow the structure of the document, where goals and review results are relatively short, and previous code contains a lot of text. In addition, research data and review may both contain parts of Python code and as the complexity grows, it is harder for the model to stay focused and not mix up real code with quoutes from other parts of the prompt.

To make it simpler for the model, the prompt is supplied in multiple parts: the prompt from `scripts/*.md`, the use case, goals and research data are all combined into one system prompt (making it cacheable and saving processing tokens), followed by the code, program output and review results as separate parts. **It is much easier for the model to receive data this way.**  

#### Code quality gate

`code_quality_gate()` is called to check the model's code/diff output blocks. The model's output generation sometimes misoperates and generates long sequences of the same character (`kkkkkkk`...), or repeats the same line or a block of lines multiple times until it hits its output token limit. Continuing iterations from such a code makes no sense and the iteration is restarted.

Current `code_quality_gate()` implementations only detects very long lines and sequences of repeating lines as bad quality, which is sufficient to detect failures in 90% of cases.

#### Unified Diff

The agent accepts unified diffs as model output. When fixing bugs or adding features, a diff format allows to limit the number of output tokens. See `./patch.py` for implementation.

The agent accepts both normal unified diffs and diffs without line number information (in [aider udiff syntax](https://aider.chat/docs/more/edit-formats.html), alhough not using aider code). Line numbers are not used to match chunks, as LLMs are typically bad at counting and output wrong line numbers anyway. As the agent only works on one file, all chunks shall be related to the same file.

There are also certain guardrails in place to mitigate issues in LLM-generated diffs:

- Chunks are matched in a search-and-replace way, the header information is not used;
- The code reduces the number of starting and leading context lines, as the model often outputs too many of them, making it hard to match the chunk;
- The code tries to fix issues where the model puts `+`, `-` and ` ` incorrectly;
- The code tries to do fuzzy matching;
- If some chunks can't be applied, the agent continues anyway.

While a unified diff is reducing the number of output tokens, it creates a hurdle in the content generation process for the model, and it may be beneficial to disable it when the model is operating close to it's full capacity.

#### Code execution

Code received from the model is executed in a sandboxed environment. Its `stdout`, `stderr`, and an exit code are then provided to the Reviewer sub-agent as well to the next Coder run.

There are some reasons to use local execution environment and not rely on the `code_execution` tool of Gemini, which is also capable of executing Python code:

- We want a resulting code that runs on the local machine;
- We want a precise way to of evaluating the code generation;
- The model seems reluctant to run its own code before outputting, especially when the task is complex. It tends to fully hallucinate the code output, and it is then not suitable for the Review: while hallucinated output shows that all tests pass, in reality it may not be so. Passing these hallucinated results into Reviewer and Coder model would make it even worse.

It it actually very benefitial to have the model execute its code before returning it and we ask it to do so in the `scripts/coder fix.md` prompt. In a case it is actually executing the code, the quality metric of the code increases in bigger steps per iteration, and it only grows slowly when the model does not execute. It's like the model is doing several internal "fix-test-repeat" iterations in one run when it executes the code, and only one when it relies on external execution. It is however hard to convince the model to *always* execute the code.

#### Syntax fix

If local code execution returns SyntaxError or the like, one extra post-processing step is performed to try and fix this error.

It mimics a programmer, who basically wrote correct code, and then fixes small errors here and there. The mental load to write the code and to fix issues are very different. It is much easier to fix smaller error if we stop thinking about the architecture, the goals etc.

The Syntax fix sub-agent prompt (`scripts/syntax fix.md`) is much easier than that of a Coder sub-agent. What it means in practice is the Syntax fix sub-agent is able to fix most issues quickly and with low token count. Using the full Coder+Reviewer cycle would have costed much more tokens.

> The Coder sub-agent tends to repeat its own errors again and again, even when specifically asked to fix the issue. With Syntax fix it is mitigated.

#### Reviewer

The Reviewer is a sub-agent tasked to evaluate the code and the program output against the goals. The prompt is `scripts/reviewer.md`.

If the Reviewer has different context or assumptions compared to that of the Coder, it may cyclically ask the Coder change something according to its vision. The Coder will follow what is there in its own context and repeat the implementation which the Reviewer does not like, creating a loop of misunderstanding. Hence it is important that the Coder and the Reviewer have the same context. That's why the Reviewer is provided with the use case description and  research results, and it also sees any assumptions added to the goals by the Refiner sub-agent.

The Reviewer tends to write essays about the code, which we don't want, and we ask it to generate a short TODO list with some actionable items.

It may happen that the Reviewer is asking for too many changes and then the Coder can never do what was asked. To mitigate that, the Reviewer is provided with its own previous review. If it sees that some items from the previous iteration are not fixed, it limits the TODO list to these items to make sure they are fixed.

The Reviewer sub-agent is likely to consume nearly equal amounts of tokens as the Coder sub-agent.

It may be beneficial to run both Coder and Reviewer with the same Gemini model. Having that ensures that both Coder and Reviewer have consensus about the points which are not in the Research, the Goals, or the assumptions created by the Refiner. This is not required when the task is fully and unambiguously defined and enough research data is provided.

#### Goals check

A `scripts/goals check.md` script is used to run a Goals check sub-agent, which checks if the goals are fully met. The agent outputs two values: a binary YES/NO for the goal completion, and a 0-100 completion score.

In case YES is returned, the main cycle is completed and the program proceeds to the final code generation.

In case NO is returned, the iteration is added to the iteration list along with the completion score. The list is maintained by a `Context` class instance.

#### Progress check

A `progress_check()` function is called to check if the completion score improves over iterations. If it is not the case and the completion score is actually worse than it was N iterations ago (for example: 75, 45, 55, 30), the execution is reset to the results of that best iteration (in the example: 75) and continues again from there. The idea behind that some of the steps following that best iteration just made a bad architectural choice which the model is not capable of mitigating. It is easier to retry again from that point.

The number of tolerable unsuccessful iterations is set with `--reset <N>` command line parameter and defaults to 3. To disable rollback logic, use `--no-reset`.

The `progress_check()` logic can actually improve chances to complete the task for mid-range models, like Gemini-2.5-flash.

### Agentic AI Patterns Used

#### 1. **Goal Setting and Monitoring**

Implements a sophisticated retry strategy:

- Tracks score progression across iterations
- Detects stagnation (no improvement over N iterations)
- Automatically rolls back to the last successful state
- Prevents infinite loops and wasted compute

This project is derived from the example to the the Chapter 11, "Goal Setting and Monitoring", of the book "Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems" by Antonio Gulli.

#### 2. **Multi-Agent System**

The architecture employs specialized agents with distinct roles:

- **Coder**: Generates and modifies code
- **Reviewer**: Evaluates quality and provides feedback
- **Researcher**: Perfoms research of specified URLs
- **Refiner**: Refines goals and the use case to make them full and non-conflicting

Each agent uses different model configurations optimized for its task (e.g., higher temperature for reviewer, structured output for goal checking).

> See Chapter 7 of the book.

#### 3. **Reflection Pattern**

The reviewer agent analyzes the coder's output and provides detailed feedback, which is then used to guide the next iteration. This self-reflection loop enables continuous improvement:

```txt
Code → Execute → Review → Feedback → Refined Code
```

> See Chapter 4 of the book.

#### 4. **Tool Use Pattern**

Agents leverage external tools to extend their capabilities:

- **Code Execution Tool**: Built-in Python execution in Gemini models
- **URL Context Tool**: Fetches and processes external documentation
- **Sandbox Execution**: Secure local code execution with multiple backends

> See Chapter 5 of the book.

#### 5. **Planning and Reasoning**

The system demonstrates planning through:

- **Goal Refinement**: Clarifies and structures requirements before starting
- **Research Phase**: Gathers necessary context from external sources
- **Progress Tracking**: Monitors improvement trends and adapts strategy

#### 6. **Memory and Context Management**

The `Context` class maintains state across iterations:

- Stores all previous iterations with code, feedback, and scores
- Enables the agent to learn from past attempts
- Uses system instruction caching (Gemini feature) to reduce token costs

#### 7. **Structured Output and Validation**

Uses JSON schemas to enforce output format:

- Goal evaluation returns structured `{result: "Yes"/"No", score: 0-100}`
- Goal refinement returns structured `{refined_use_case: "...", refined_goals: [...]}`
- Ensures reliable parsing and decision-making

#### 8. **Exception handling and Recovery**

As the coding agent takes multiple steps and tens of minutes to complete, handling API exceptions and model misbehaviour is a must to complet the task.

- Retry mechanism in `llm_query()` tolerates API errors;
- Syntax error detection and automatic repair
- `code_quality_gate()` makes sure model output errors are mitigated;
- Unified diff validation and fuzzy patching. `patch_code()` applies matching hunks even if some other hunks can't be applied.

> See Chapter 12 of the book.

#### 9. **Prompt Chaining**

Several sub-agents are executed in sequence, where the output of one fed as an input to another. For example: results of Reviewer are processed by the Goal Check.

> See Chapter 1 of the book.

#### 10. **Resource-Aware Optimisation**

The agent uses different models and model settings for the coding, review and utility tasks, optimising performance and cost.

> See Chapter 16 of the book.

## Output Files

The agent saves intermediate data to the `solutions/` directory, so that it is easy to debug or understand what it happening. All file names start with the same base name. Some of the files are:

- `{name}.py` - Final solution
- `{name}_v{iter}.py` - Intermediate code versions
- `{name}_coder_prompt_{iter}.md` - Prompts sent to coder
- `{name}_coder_code_{iter}.py` - Raw code blocks from coder
- `{name}_coder_diff_{iter}.patch` - Diff patches
- `{name}_review_v{iter}.txt` - Review feedback
- `{name}_v{iter}_output.txt` - Execution output
- `{name}_refined_use_case.md` - Refined problem statement
- `{name}_refined_goals.md` - Refined acceptance criteria
- `{name}_research_summary_{iter}.md` - Research results

Here, `{name}` is a unique base name like `solution_1234` and `{iter}` is the iteration number.

## Sandboxed Execution

The agent supports multiple sandbox methods for secure code execution. See **[README_SANDBOX.md](README_SANDBOX.md)** for detailed documentation and installation instructions.

**Available methods:**

- `auto` - Automatically tries Firejail → Docker → Bubblewrap (recommended)
- `firejail` - Lightweight Linux sandbox with filesystem/network isolation
- `docker` - Full container isolation, cross-platform
- `bubblewrap` - Uses linux namespaces, very lightweight, can be used with WSL
- `subprocess` - No sandboxing, dangerous, development only

## Token Usage Tracking

The agent tracks and reports:

- Input/output tokens per model
- Cached tokens (prompt caching)
- Total cost estimates
- Generation times
- Per-iteration and cumulative statistics


## Development and Customization

### Creating a New Task

1. Create a new directory in `tasks/<your-task-name>/`
2. Add the following files:
   - `config.json` - Task configuration
   - `hl_spec.md` - High-level use case description
   - `ac.md` - Acceptance criteria and goals
   - `README.md` - Task documentation

3. Run the agent:

```bash
python coding_agent.py <your-task-name>
```

### Customizing Prompts

Edit the prompt templates in the `scripts/` directory to change how the agent:

- Generates code (`coder create.md`, `coder fix.md`)
- Reviews solutions (`reviewer.md`)
- Checks goals (`goals check.md`)
- Refines requirements (`refine task.md`)
- Conducts research (`research.md`)
- Fixes syntax errors (`syntax fix.md`)

### Tuning Model Selection

Different models have different strengths:

- **gemini-2.5-flash-lite**: Fast, low-cost, good for simple tasks
- **gemini-2.5-flash**: Balanced performance and cost
- **gemini-2.5-pro**: High quality, better for complex tasks
- **gemini-3-pro-preview**: Cutting-edge, best results for hard problems

Configure models per task in `config.json`.
