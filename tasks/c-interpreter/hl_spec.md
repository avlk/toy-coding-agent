Write a C-like language interpreter. It shall have a parser, a type checker, and an code execution stages.

The interpreter shall be able to execute simple programs written in this language.

The interpreter shall have one main entry point function called interpreter_main(str), where str contains multi-line text of the program.

When the program is run from a command line, program code is provided to the interpreter as a text file whose path is passed as a commandline argument. 

The file is read and its content is executed with interpreter_main().

The program also has embedded test mode.  When run with a "--test" flag, the program runs all tests defined in TEST_PROGRAMS.

The language shall support basic data types (integers, booleans, strings), control structures (if-else, for and while loops), and functions.

The interpreter shall be able to handle syntax errors and runtime errors gracefully.

The I/O in this language is through stdin and stdout only and there is a native print() command to print whatever is passed into it and 
read_int(), read_bool() and read_str() statements to read user input.

A test set of programs shall be provided to validate the interpreter's functionality as a list of dictionaries of the following structure:

```
TEST_PROGRAMS = [
    { "code": "<program code as string>", 
    "description": "<short description of what the program does>", 
    "expected_output": "<expected output when the program is run>",
    "inputs": [<list of bool, int and string inputs for the program>]
    },
    ...
]
```

In a test mode, program code provided by "code" is passed as a string input to the interpreter, the output is is accumulated into "output" line-by-line and then compared against "expected_output".

"inputs" are mocking any real read_int(), read_bool() and read_str() calls in the program.

When running tests, for each test the status PASS or FAIL shall be recorded along with any error messages for failed tests. 

At the end of test run, total number of tests and number of passed tests shall be printed.

A test suite shall include, among others, tests for: recursion, complex expressions inside function call parameters and control structures.

The number of test programs shall be kept reasonable (preferably below 100) to not overflow the LLM context window.
Minimize test program number by combining multiple tests into one where possible.
Minimize test program length to save program size and do not insert comments into test cases.

An embedded markdown documentation of the language syntax and features shall be provided as a multi-line string variable called LANGUAGE_SPECIFICATION.

When run from command line with "--syntax" flag, the program shall print this documentation to stdout and exit.

Make sure that the interpreter compiles and runs the test programs by using the code_execution tool before submitting the result.
