Implement a program for the following use case:

Develop a C-like language interpreter comprising a parser, type checker, and code executor.

The interpreter must execute simple programs, supporting basic data types (integers, booleans, strings),
control structures (if-else, for, while loops), and functions, including recursion. It will have a main
entry point interpreter_main(str) for programmatic use. Command-line execution will support running programs
from a file, displaying language documentation via --syntax, and executing an embedded test suite via --test.

I/O is restricted to stdin/stdout using native print(), read_int(), read_bool(), and read_str() commands. 
The interpreter must gracefully handle syntax and runtime errors.

A TEST_PROGRAMS list, structured as dictionaries, will validate functionality, mocking inputs and comparing outputs.
Test results (PASS/FAIL, error messages, total/passed counts) must be reported.
An embedded LANGUAGE_SPECIFICATION markdown string will document the language.
