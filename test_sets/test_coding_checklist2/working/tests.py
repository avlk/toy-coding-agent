from typing import List, Dict, Any, Optional, Callable, Tuple
from interpreter import interpreter_main

TEST_PROGRAMS: List[Dict[str, Any]] = [
    {
        "name": "Basic Integer Arithmetic",
        "code": """
            void main() {
                int x = 10;
                int y = 5;
                print(x + y);
                print(x - y);
                print(x * y);
                print(x / y);
                print(x % y);
            }
        """,
        "input": [],
        "expected_output": ["15", "5", "50", "2", "0"],
        "expected_error": None,
    },
    {
        "name": "If-Else Statement",
        "code": """
            void main() {
                int x = 10;
                if (x > 5) {
                    print("x is greater than 5");
                } else {
                    print("x is not greater than 5");
                }
            }
        """,
        "input": [],
        "expected_output": ["x is greater than 5"],
        "expected_error": None,
    },
    {
        "name": "Function Call and Return",
        "code": """
            int add(int a, int b) {
                return a + b;
            }
            void main() {
                int result = add(7, 3);
                print(result);
            }
        """,
        "input": [],
        "expected_output": ["10"],
        "expected_error": None,
    },
    {
        "name": "Division by Zero Error",
        "code": """
            void main() {
                int x = 10;
                int y = 0;
                print(x / y);
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "RuntimeError: Division by zero", # Placeholder for expected error message
    },
    {
        "name": "Undefined Variable Error",
        "code": """
            void main() {
                print(undefined_var);
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "RuntimeError: Undefined variable 'undefined_var'", # Placeholder
    },
    {
        "name": "Syntax Error - Missing Semicolon",
        "code": """
            void main() {
                int x = 10
                print(x);
            }
        """,
 "input": [],
 "expected_output": [],
 "expected_error": "SyntaxError: Expected ';', got 'print' at line 4, column 17", # Updated expected error
    },
    {
        "name": "For Loop - Basic",
        "code": """
            void main() {
                int i;
                for (i = 0; i < 3; i = i + 1) {
                    print(i);
                }
            }
        """,
        "input": [],
        "expected_output": ["0", "1", "2"],
        "expected_error": None,
    },
    {
        "name": "While Loop - Basic",
        "code": """
            void main() {
                int i = 0;
                while (i < 3) {
                    print(i);
                    i = i + 1;
                }
            }
        """,
        "input": [],
        "expected_output": ["0", "1", "2"],
        "expected_error": None,
    },
    {
        "name": "Function Recursion - Factorial",
        "code": """
            int factorial(int n) {
                if (n == 0) {
                    return 1;
                } else {
                    return n * factorial(n - 1);
                }
            }
            void main() {
                print(factorial(4)); // Expected: 24
            }
        """,
        "input": [],
        "expected_output": ["24"],
        "expected_error": None,
    },
    {
        "name": "String Concatenation",
        "code": """
            void main() {
                string s1 = "Hello";
                string s2 = " World";
                print(s1 + s2);
            }
        """,
        "input": [],
        "expected_output": ["Hello World"],
        "expected_error": None,
    },
    {
        "name": "Boolean Logic",
        "code": """
            void main() {
                bool t = true;
                bool f = false;
                print(t && f);
                print(t || f);
                print(!f);
            }
        """,
        "input": [],
        "expected_output": ["false", "true", "true"], # Corrected expected output
        "expected_error": None,
    },
    {
        "name": "Read Int - Valid Input",
        "code": """
            void main() {
                int num = read_int();
                print(num + 1);
            }
        """,
        "input": ["123"],
        "expected_output": ["124"],
        "expected_error": None,
    },
    {
        "name": "Read Int - Invalid Input",
        "code": """
            void main() {
                int num = read_int();
                print(num);
            }
        """,
        "input": ["abc"],
        "expected_output": [],
        "expected_error": "RuntimeError: Invalid input for read_int: 'abc'. Expected an integer.",
    },
    {
        "name": "If-Else without Else",
        "code": """
            void main() {
                int x = 10;
                if (x > 5) {
                    print("Only if");
                }
                if (x < 5) {
                    print("Should not print");
                }
            }
        """,
        "input": [],
        "expected_output": ["Only if"],
        "expected_error": None,
    },
    {
        "name": "Nested If-Else",
        "code": """
            void main() {
                int x = 10;
                if (x > 5) {
                    if (x < 15) {
                        print("Nested true");
                    } else {
                        print("Nested false");
                    }
                } else {
                    print("Outer false");
                }
            }
        """,
        "input": [],
        "expected_output": ["Nested true"],
        "expected_error": None,
    },
    {
        "name": "For Loop - No Init/Increment",
        "code": """
            void main() {
                int i = 0;
                for (; i < 2; ) {
                    print(i);
                    i = i + 1;
                }
            }
        """,
        "input": [],
        "expected_output": ["0", "1"],
        "expected_error": None,
    },
    {
        "name": "Type Mismatch - Assignment",
        "code": """
            void main() {
                int x = true;
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: Cannot assign bool to int variable 'x'",
    },
    {
        "name": "Type Mismatch - Binary Op",
        "code": """
            void main() {
                int x = 10;
                bool y = true;
                print(x + y);
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: Incompatible types for '+' operation: int and bool",
    },
    {
        "name": "Type Mismatch - Unary Op",
        "code": """
            void main() {
                int x = 10;
                print(!x);
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: Incompatible type for '!' operation: int",
    },
    {
        "name": "Type Mismatch - Function Call Arg",
        "code": """
            int add(int a, int b) { return a + b; }
            void main() {
                add(1, true);
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: Argument 2 of function 'add' expected int, got bool",
    },
    {
        "name": "Return Type Mismatch - Int Func Returns Bool",
        "code": """
            int getBool() {
                return true;
            }
            void main() {
                int x = getBool();
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: Cannot return bool from function expecting int",
    },
    {
        "name": "Return Type Mismatch - Void Func Returns Value",
        "code": """
            void doSomething() {
                return 1;
            }
            void main() {
                doSomething();
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: Void function cannot return a value",
    },
    {
        "name": "Non-Void Function Not Returning Value",
        "code": """
            int getValue() {
                // Missing return statement
            }
            void main() {
                getValue();
            }
        """,
        "input": [],
        "expected_output": [], # No output expected
        "expected_error": "TypeError: Function 'getValue' expected to return int, but returned nothing at line 2, column 13",
    },
    {
        "name": "Variable Redeclaration Error",
        "code": """
            void main() {
                int x = 10;
                int x = 20;
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: Redeclaration of 'x' in the same scope",
    },
    {
        "name": "Access Variable Before Declaration Error",
        "code": """
            void main() {
                x = 10;
                int x;
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "RuntimeError: Undefined variable 'x'",
    },
    {
        "name": "Condition Not Boolean Error - If",
        "code": """
            void main() {
                int x = 10;
                if (x) {
                    print("hello");
                }
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: If statement condition must be of type bool, got int",
    },
    {
        "name": "Condition Not Boolean Error - While",
        "code": """
            void main() {
                int x = 1;
                while (x) {
                    print("loop");
                    x = x - 1;
                }
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: While loop condition must be of type bool, got int",
    },
    {
        "name": "Condition Not Boolean Error - For",
        "code": """
            void main() {
                for (int i = 0; i; i = i + 1) {
                    print("loop");
                }
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "TypeError: For loop condition must be of type bool, got int",
    },
    {
        "name": "Unmatched Delimiter Error - Brace",
        "code": """
            void main() {
                print("hello");
            // Missing closing brace
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "SyntaxError: Expected '}', got EOF",
    },
    {
        "name": "Unmatched Delimiter Error - Parenthesis",
        "code": """
            void main() {
                print("hello"; // Missing closing parenthesis
            }
        """,
        "input": [],
        "expected_output": [],
        "expected_error": "SyntaxError: Expected ')', got ';'",
    },
]


def run_tests():
    """
    Executes all tests defined in TEST_PROGRAMS and reports results.
    """
    print("Running embedded test suite...")
    total_tests = len(TEST_PROGRAMS)
    passed_tests = 0

    for i, test in enumerate(TEST_PROGRAMS):
        test_name = test["name"]
        code = test["code"]
        input_mock = test.get("input", [])
        expected_output = test.get("expected_output", [])
        expected_error = test.get("expected_error", None)

        print(f"\n--- Test {i+1}/{total_tests}: {test_name} ---")
        actual_output: List[str] = []
        actual_error: Optional[str] = None

        captured_output, actual_error = interpreter_main(code, input_mock=input_mock, test_name=test_name)
        if captured_output is not None:
            actual_output = captured_output
        
        test_passed = True
        if expected_error:
            if actual_error and expected_error in actual_error:
                print(f"  PASS: Expected error '{expected_error}' found.")
            else:
                print(f"  FAIL: Expected error '{expected_error}', but got '{actual_error}' or no error.")
                test_passed = False
        elif actual_error:
            print(f"  FAIL: Unexpected error occurred: {actual_error}")
            test_passed = False
        
        if test_passed and actual_output != expected_output:
            print(f"  FAIL: Output mismatch.")
            print(f"    Expected: {expected_output}")
            print(f"    Actual:   {actual_output}")
            test_passed = False
        elif test_passed and not expected_error: # Only print pass if no error expected and output matches
            print(f"  PASS: Output matches expected.")

        if test_passed:
            passed_tests += 1
        else: # Only print code if test failed
            print(f"  Code:\n{code}")

    print(f"\n--- Test Summary ---")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    return passed_tests == total_tests

