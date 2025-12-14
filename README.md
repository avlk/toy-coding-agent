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

For Firejail (lightweight, Linux):
```bash
sudo apt-get install firejail
```

For Docker (full isolation):
```bash
# See https://docs.docker.com/get-docker/
```

For Bubblewrap (Linux namespaces):
```bash
sudo apt-get install bubblewrap
```

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
python coding_agent.py qr --no-refine-goals

# Run with no automatic resets
python coding_agent.py 3d-ball --no-reset

# Run without using diffs
python coding_agent.py c-interpreter --no-diffs
```

## Available Tasks

The `tasks/` directory contains several pre-configured tasks:

### 1. **8-queens** (Difficulty: Easy)
Solve the classic 8 Queens problem and print all solutions. A simple algorithmic task suitable for testing the basic workflow.

### 2. **qr** (Difficulty: Medium-Hard)
Generate QR codes that are readable by smartphones without using external QR encoding libraries. Requires research from external URLs to understand the QR code standard. Tests the agent's ability to implement complex protocols.

### 3. **3d-ball** (Difficulty: Medium)
Create ASCII art animation of a rotating 3D sphere. Tests geometric calculations and visualization.

### 4. **c-interpreter** (Difficulty: Hard)
Implement a subset of a C language interpreter. Tests parser design and language implementation skills.

### 5. **upc** (Difficulty: Medium)
Universal Product Code (barcode) generator and validator.

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
  "max_rounds": 25,
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
- `coder_model`: Model for code generation (e.g., gemini-2.5-pro, gemini-3-pro-preview)
- `reviewer_model`: Model for code review and feedback
- `utility_model`: Model for utility tasks (goal checking, research)
- `max_rounds`: Maximum iteration count
- `basename`: Prefix for generated solution files
- `sandbox_method`: Execution environment (auto, firejail, docker, bubblewrap, subprocess)
- `commandline_args`: Arguments to pass when executing the generated code
- `urls`: External documentation URLs for research phase (optional)
- `python_packages`: Extra packages to install in sandbox venv (optional)

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

Generated files are saved to the `solutions/` directory with the following naming convention:

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

Where `{name}` is a unique identifier like `solution_1234` and `{iter}` is the iteration number.

## Sandboxed Execution

The agent supports multiple sandbox methods for secure code execution:

### Auto (Recommended)
Tries methods in order: Firejail → Docker → Bubblewrap

### Firejail (Lightweight, Linux)
- No network access
- Limited filesystem access
- Private /tmp directory
- No privilege escalation

### Docker (Full Isolation)
- Complete filesystem isolation
- Resource limits (512MB RAM, 1 CPU)
- Works on Linux, macOS, Windows
- Slower startup due to container overhead

### Bubblewrap (Linux Namespaces)
- Uses Linux kernel namespaces
- No network access
- Limited filesystem access

See `README_SANDBOX.md` for detailed sandbox configuration.

## Token Usage Tracking

The agent tracks and reports:
- Input/output tokens per model
- Cached tokens (prompt caching)
- Total cost estimates
- Generation times
- Per-iteration and cumulative statistics

## Project Structure

```
coding-agent/
├── coding_agent.py          # Main agent implementation
├── patch.py                 # Unified diff parsing and application
├── sandbox_execution.py     # Secure code execution backends
├── token_tracker.py         # Token usage monitoring
├── utils.py                 # Utility functions
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── README_SANDBOX.md       # Sandbox configuration details
├── scripts/                # LLM prompt templates
│   ├── coder create.md
│   ├── coder fix.md
│   ├── reviewer.md
│   ├── goals check.md
│   ├── refine task.md
│   ├── research.md
│   └── syntax fix.md
├── tasks/                  # Task definitions
│   ├── 8-queens/
│   ├── qr/
│   ├── 3d-ball/
│   ├── c-interpreter/
│   └── upc/
└── solutions/             # Generated solutions (created at runtime)
```

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

## Contributing

Contributions are welcome! Areas for improvement:
- Sandbox evaluation
- Enhanced error recovery strategies
- Better progress metrics and visualization

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

### Sandbox Failures
If sandboxing fails, the agent will report which method was attempted. Try:
1. Install the recommended sandbox tool (Firejail is easiest)
2. Use Docker for maximum compatibility
3. Set `sandbox_method: "subprocess"` in config.json (less secure)

### Token Limits
If hitting token limits:
- Use smaller models (gemini-2.5-flash-lite)
- Reduce `max_rounds` in config.json
- Enable diffs mode (`--diffs`) to reduce context size

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
