# AI Code Generation Agent

An agentic AI system that autonomously generates, tests, and iteratively refines Python code to meet specified requirements. The agent uses Google's Gemini models in a multi-stage workflow with feedback loops, combining multiple AI design patterns to achieve reliable code generation.

## Overview

This coding agent implements an iterative development workflow where AI models collaborate to:
1. **Refine** the problem statement and acceptance criteria
2. **Research** external documentation and resources
3. **Generate** Python code that meets the requirements
4. **Execute** the code in a secure sandbox environment
5. **Review** the output against goals
6. **Iterate** until the solution is complete or max iterations reached

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
- `--reset N`: Reset to last successful iteration after N unsuccessful attempts (default: 3)
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
The model does not require any external sources to complete the task as it already knows about the problem from its learning set,
it may already have seen some solutions and it can of course code.

### 2. **3d-ball** (Difficulty: Easy)
Create ASCII art animation of a 3D sphere throwing a shadow onto a plane.
While the model is aware of geometric calculations and basic visualization options from its training data,
it takes some effort to assess if the picture is rendered correctly.

### 3. **c-interpreter** (Difficulty: Medium)
Design a C-like language and implement its interpreter along with the test suite.
It tests the models ability to design a language, plan implementation steps, create a set of tests and fix the code.
The code does not come out perfect or even feature-complete after the first run and it takes significant effort to get it done.
While it was expected to be a hard task, it is not that hard actually, as the model does not need any external context for the task completion:
it knows plenty about programming languages, testing, reviewing code and it can code very well.

### 4. **upc** (Difficulty: Hard)
Barcode generator and validator. A Code-128 barcode generator is not the hardest thing to do. What it does is basically just take a table mapping input characters to the bar sequences, map input data to the output sequence and print it. Surprisingly, it is a hard task for an LLM, as it does not know any of these mappings by heart. To make the model use the right mapping, resource URLs are provided which are parsed by a Researcher sub-agent and fed into the prompt. The data from the researcher is filling up the context window and makes the model think about it, summarize the data, which generally reduces the amount of tokens and context left for thinking and writing correct code.

### 5. **qr** (Difficulty: Hardest)
Generate QR codes that are readable by smartphones without using external QR encoding libraries. Requires research from external URLs to understand the QR code standard.While being of the same type as the **upc** task, it brings much more complexity: 1) The codes are using GF(2^8) math, and the model is generally not good at math, and it is much less good at Galois field calculations. GF(2^8) math can't be quickly proven by it's internal Python interpreter. It would be fair to say that the model knows about Galois fields, of course, it just misses some details here and there. 2) The code is two-dimensional and code point locations are much easier to show in a picture than to explain with words, but the model only receives words. It's really, really hard to understand the logic behind QR code pixel placement by only reading words. 3) The QR code uses Reed-Solomon error correction which is another layer of mathematical complexity for the model. 4) The model has to select and use some non-trivial way to test the code readability. Overall, after the model processes and understands everything it needs to complete the coding round, it has not too many tokens left for thinking and tool use. Gemini-2.5-flash model is usually quite quickly overwhelmed with the complexity, fails to run the code execution tool to proofread its code, generates faulty diffs and often repeats its previous errors. It is not impossible, but hard to reach the goals when not using Gemini-3-pro for this task.


## Task Configuration

Each task is defined in `tasks/<task-name>/` with the following structure:

```
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
- `python_packages`: Extra packages to install in sandbox venv to make local execution successful (optional). The code_execution tool of the model has a limited set of packages in its cloud shell. The model may decide to use any of those if not limited by the prompt. Make sure that your local execution environment has enough packages installed so that it does not fail on `import` directive.

A list of models: gemini-2.5-flash-lite, gemini-2.5-flash, gemini-2.5-pro, gemini-3-pro-preview.

A list of packages the code_exection tool has access to: attrs, chess, contourpy, fpdf, geopandas, imageio, jinja2, joblib, jsonschema, jsonschema-specifications, lxml, matplotlib, mpmath, numpy, opencv-python, openpyxl, packaging, pandas, pillow, protobuf, pylatex, pyparsing, PyPDF2, python-dateutil, python-docx, python-pptx, reportlab, scikit-learn, scipy, seaborn, six, striprtf, sympy, tabulate, tensorflow,toolz, xlrd.

## Architecture

### Main Execution Cycle

The agent follows a sophisticated iterative workflow combining multiple agentic AI patterns:

```
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


### Agentic AI Patterns Used

#### 1. **Multi-Agent System**
The architecture employs specialized agents with distinct roles:
- **Coder Agent**: Generates and modifies code
- **Reviewer Agent**: Evaluates quality and provides feedback
- **Utility Agent**: Handles auxiliary tasks (goal checking, research)

Each agent uses different model configurations optimized for its task (e.g., higher temperature for reviewer, structured output for goal checking).

#### 2. **Reflection Pattern**
The reviewer agent analyzes the coder's output and provides detailed feedback, which is then used to guide the next iteration. This self-reflection loop enables continuous improvement:
```
Code → Execute → Review → Feedback → Refined Code
```

#### 3. **Tool Use Pattern**
Agents leverage external tools to extend their capabilities:
- **Code Execution Tool**: Built-in Python execution in Gemini models
- **URL Context Tool**: Fetches and processes external documentation
- **Sandbox Execution**: Secure local code execution with multiple backends

#### 4. **Planning and Reasoning**
The system demonstrates planning through:
- **Goal Refinement**: Clarifies and structures requirements before starting
- **Research Phase**: Gathers necessary context from external sources
- **Progress Tracking**: Monitors improvement trends and adapts strategy

#### 5. **Memory and Context Management**
The `Context` class maintains state across iterations:
- Stores all previous iterations with code, feedback, and scores
- Enables the agent to learn from past attempts
- Uses system instruction caching (Gemini feature) to reduce token costs

#### 6. **Iterative Refinement with Rollback**
Implements a sophisticated retry strategy:
- Tracks score progression across iterations
- Detects stagnation (no improvement over N iterations)
- Automatically rolls back to the last successful state
- Prevents infinite loops and wasted compute

#### 7. **Structured Output and Validation**
Uses JSON schemas to enforce output format:
- Goal evaluation returns structured `{result: "Yes"/"No", score: 0-100}`
- Goal refinement returns structured `{refined_use_case: "...", refined_goals: [...]}`
- Ensures reliable parsing and decision-making

#### 8. **Error Recovery and Self-Correction**
Multiple layers of error handling:
- Syntax error detection and automatic repair
- Code quality gates (reject obviously broken outputs)
- Unified diff validation and fuzzy patching
- Automatic retry on server errors with exponential backoff

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

## License

Copyright (c) 2025 Andrey Volkov

This work is a derivative work based on the original by Mahtab Syed.
Original author copyright notice:
- MIT License
- Copyright (c) 2025 Mahtab Syed
- https://www.linkedin.com/in/mahtabsyed/

## Troubleshooting

### API Key Issues
```bash
# Ensure your API key is set
echo $GEMINI_API_KEY
# If empty, set it:
export GEMINI_API_KEY="your-key"
```

### Sandbox Issues
See **[README_SANDBOX.md](README_SANDBOX.md)** for installation, troubleshooting, and security considerations.

### Model Errors
If seeing server errors or rate limits:
- The agent automatically retries with backoff
- Consider using lower-tier models
- Check your API quota

## Acknowledgments

This project builds upon concepts from:
- Agentic AI design patterns
- Reflection and self-correction in LLMs
- Multi-agent systems
- Automated program synthesis

Original inspiration and code by Mahtab Syed.
