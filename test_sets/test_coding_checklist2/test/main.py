import sys
import argparse
from tests import run_tests
from interpreter import interpreter_main

# Part 1: Language Specification
LANGUAGE_SPECIFICATION = """
# C-like Language Specification

This document outlines the syntax and features of the simplified C-like language interpreter.

## Data Types
- `int`: Integer numbers (e.g., `10`, `-5`).
- `bool`: Boolean values (`true`, `false`).
- `string`: String literals (e.g., `"hello world"`).
- `void`: Used for functions that do not return a value.

## Variables
Variables must be declared with a type before use.
Example: `int x;`, `bool is_active = true;`, `string name = "Alice";`

## Operators
### Arithmetic Operators
- `+`, `-`, `*`, `/`, `%` (addition, subtraction, multiplication, division, modulo)
### Relational Operators
- `==`, `!=`, `<`, `>`, `<=`, `>=` (equality, inequality, less than, greater than, less than or equal, greater than or equal)
### Logical Operators
- `&&` (AND), `||` (OR), `!` (NOT)
### Assignment Operator
- `=`

## Control Structures
### If-Else Statement
```c
if (condition) {
    // statements if condition is true
} else {
    // statements if condition is false
}
```
The `else` block is optional.

### For Loop
```c
for (initialization; condition; increment) {
    // loop body
}
```

### While Loop
```c
while (condition) {
    // loop body
}
```

## Functions
Functions can be declared with a return type and parameters. Recursion is supported.
```c
int add(int a, int b) {
    return a + b;
}

void main() {
    int result = add(5, 3);
    // ...
}
```
`void` indicates no return value.

## Built-in I/O Functions
- `print(expression)`: Prints the value of the expression to stdout.
- `read_int()`: Reads an integer from stdin.
- `read_bool()`: Reads a boolean (`true`/`false`) from stdin.
- `read_str()`: Reads a string from stdin.

## Comments
Single-line comments start with `//`.
Multi-line comments are enclosed in `/* ... */`.

## Error Handling
The interpreter provides descriptive error messages for:
- Syntax errors (e.g., missing semicolons, unmatched delimiters).
- Runtime errors (e.g., division by zero, type mismatches, undefined variables/functions, invalid input for `read_int`/`read_bool`).
"""

def main():
    """
    Main function for command-line execution.
    Handles --syntax, --test, and file execution.
    """
    parser = argparse.ArgumentParser(description="A C-like language interpreter.")
    parser.add_argument("file", nargs="?", help="Path to the program file to execute.")
    parser.add_argument("--syntax", action="store_true", help="Display language syntax documentation.")
    parser.add_argument("--test", action="store_true", help="Run the embedded test suite.")

    args = parser.parse_args()

    if args.syntax:
        print(LANGUAGE_SPECIFICATION)
        sys.exit(0)

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    if args.file:
        try:
            with open(args.file, "r") as f:
                program_code = f.read()
            print(f"Executing program from '{args.file}'...")
            # interpreter_main returns output_capture and actual_error, but for CLI we just print
            _, error = interpreter_main(program_code)
            if error:
                print(f"Execution Error: {error}", file=sys.stderr)
                sys.exit(1)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An error occurred while reading or executing the file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("No file provided. Use --syntax for documentation or --test to run tests.")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()