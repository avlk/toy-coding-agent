import sys
import re
import argparse
from collections import deque

# --- LANGUAGE SPECIFICATION ---
LANGUAGE_SPECIFICATION = """
# C-like Language Specification

This document describes the syntax and features of our simple C-like language.

## Data Types
- `int`: Integer numbers (e.g., `10`, `-5`).
- `bool`: Boolean values (`true`, `false`).
- `string`: Sequences of characters enclosed in double quotes (e.g., `"hello"`).

## Variables
Variables must be declared with a type before use.
Syntax: `type identifier;` or `type identifier = expression;`
Example:
```c
int x;
int y = 10;
string name = "Alice";
bool is_active = true;
```

## Operators
### Arithmetic Operators
- `+`, `-`, `*`, `/`, `%` (addition, subtraction, multiplication, division, modulo)
### Comparison Operators
- `==`, `!=`, `<`, `>`, `<=`, `>=` (equality, inequality, less than, greater than, less than or equal to, greater than or equal to)
### Logical Operators
- `&&` (AND), `||` (OR), `!` (NOT)

## Control Structures
### If-Else Statement
Syntax:
```c
if (condition) {
    // statements if condition is true
} else {
    // statements if condition is false
}
```
The `else` block is optional.

### While Loop
Syntax:
```c
while (condition) {
    // statements to repeat while condition is true
}
```

### For Loop
Syntax:
```c
for (initialization; condition; increment) {
    // statements to repeat
}
```
`initialization` and `increment` parts can be empty.

## Functions
Functions can be declared with a return type, name, and parameters.
The `void` keyword can be used for functions that do not return a value.
Syntax:
```c
type function_name(type param1, type param2) {
    // function body
    return expression; // optional, depends on return type (void functions don't return)
}
```
Example:
```c
int add(int a, int b) {
    return a + b;
}

void greet(string name) {
    print("Hello, " + name);
}
```
Functions can be called by their name with arguments.
Example: `add(5, 3);`

## Input/Output
- `print(expression)`: Prints the value of the expression to standard output, followed by a newline.
- `read_int()`: Reads an integer from standard input.
- `read_bool()`: Reads a boolean (`true` or `false`) from standard input.
- `read_str()`: Reads a string from standard input.
"""

# --- Custom Exceptions ---
class InterpreterError(Exception):
    """Base class for interpreter errors."""
    pass

class SyntaxError(InterpreterError):
    """Raised when a syntax error is encountered."""
    def __init__(self, message, line=None, column=None):
        super().__init__(f"Syntax Error: {message}" + (f" at line {line}, column {column}" if line else ""))
        self.line = line
        self.column = column

class RuntimeError(InterpreterError):
    """Raised when a runtime error occurs."""
    def __init__(self, message, line=None, column=None):
        super().__init__(f"Runtime Error: {message}" + (f" at line {line}, column {column}" if line else ""))
        self.line = line
        self.column = column

class TypeError(InterpreterError):
    """Raised when a type mismatch occurs."""
    def __init__(self, message, line=None, column=None):
        super().__init__(f"Type Error: {message}" + (f" at line {line}, column {column}" if line else ""))
        self.line = line
        self.column = column

# --- Lexer ---
class Token:
    def __init__(self, type, value, line=None, column=None):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, line={self.line}, col={self.column})"

class Lexer:
    KEYWORDS = {
        'int', 'bool', 'string', 'void', 'if', 'else', 'while', 'for', 'true', 'false',
        'return', 'print', 'read_int', 'read_bool', 'read_str'
    }
    TYPES = {'int', 'bool', 'string', 'void'} # Added 'void' as a type

    TOKEN_SPECS = [
        ('SKIP', r'\s+|//.*|/\*[\s\S]*?\*/'), # Whitespace, single-line comments, multi-line comments
        ('KEYWORD', r'\b(int|bool|string|void|if|else|while|for|true|false|return|print|read_int|read_bool|read_str)\b'),
        ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
        ('INTEGER', r'\b\d+\b'),
        ('STRING', r'"([^"\\]|\\.)*"'),
        ('OP_ASSIGN', r'='),
        ('OP_EQ', r'=='), ('OP_NE', r'!='), ('OP_LE', r'<='), ('OP_GE', r'>='),
        ('OP_LT', r'<'), ('OP_GT', r'>'),
        ('OP_PLUS', r'\+'), ('OP_MINUS', r'-'), ('OP_MUL', r'\*'), ('OP_DIV', r'/'), ('OP_MOD', r'%'),
        ('OP_AND', r'&&'), ('OP_OR', r'\|\|'), ('OP_NOT', r'!'),
        ('LPAREN', r'\('), ('RPAREN', r'\)'),
        ('LBRACE', r'\{'), ('RBRACE', r'\}'),
        ('SEMICOLON', r';'),
        ('COMMA', r','),
    ]

    def __init__(self, text):
        self.text = text
        self.tokens = []
        self.line = 1
        self.column = 1
        self._tokenize()

    def _tokenize(self):
        token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.TOKEN_SPECS)
        for match in re.finditer(token_regex, self.text):
            token_type = match.lastgroup
            token_value = match.group(token_type)

            if token_type == 'SKIP':
                newlines = token_value.count('\n')
                self.line += newlines
                if newlines > 0:
                    self.column = len(token_value) - token_value.rfind('\n')
                else:
                    self.column += len(token_value)
                continue

            # Adjust line/column for the token
            token_line = self.line
            token_column = self.column
            self.column += len(token_value)

            if token_type == 'KEYWORD':
                if token_value in self.TYPES:
                    token_type = 'TYPE'
                elif token_value == 'true' or token_value == 'false':
                    token_type = 'BOOLEAN'
                else: # Convert keywords like 'if', 'else' to their uppercase type
                    token_type = token_value.upper()
            elif token_type == 'IDENTIFIER' and token_value in self.KEYWORDS:
                 token_type = token_value.upper() # e.g., IF, ELSE, WHILE

            self.tokens.append(Token(token_type, token_value, token_line, token_column))
        self.tokens.append(Token('EOF', None, self.line, self.column)) # End of File token

    def get_tokens(self):
        return self.tokens

# --- AST Nodes ---
class ASTNode:
    def __init__(self, token=None):
        self.token = token
        self.line = token.line if token else None
        self.column = token.column if token else None

    def __repr__(self):
        return self.__class__.__name__

class Program(ASTNode):
    def __init__(self, statements):
        super().__init__()
        self.statements = statements

class Statement(ASTNode):
    pass

class Expression(ASTNode):
    pass

class Literal(Expression):
    def __init__(self, token, value, type_name):
        super().__init__(token)
        self.value = value
        self.type_name = type_name # 'int', 'bool', 'string'

    def __repr__(self):
        return f"Literal({self.value}, type={self.type_name})"

class Identifier(Expression):
    def __init__(self, token):
        super().__init__(token)
        self.name = token.value

    def __repr__(self):
        return f"Identifier({self.name})"

class VariableDecl(Statement):
    def __init__(self, type_token, id_token, expr=None):
        super().__init__(type_token)
        self.var_type = type_token.value
        self.name = id_token.value
        self.expression = expr

    def __repr__(self):
        return f"VariableDecl(type={self.var_type}, name={self.name}, expr={self.expression})"

class Assignment(Statement):
    def __init__(self, id_token, expr):
        super().__init__(id_token)
        self.name = id_token.value
        self.expression = expr

    def __repr__(self):
        return f"Assignment(name={self.name}, expr={self.expression})"

class BinaryOp(Expression):
    def __init__(self, left, op_token, right):
        super().__init__(op_token)
        self.left = left
        self.op = op_token.value
        self.right = right

    def __repr__(self):
        return f"BinaryOp({self.left} {self.op} {self.right})"

class UnaryOp(Expression):
    def __init__(self, op_token, right):
        super().__init__(op_token)
        self.op = op_token.value
        self.right = right

    def __repr__(self):
        return f"UnaryOp({self.op} {self.right})"

class IfStatement(Statement):
    def __init__(self, if_token, condition, true_block, else_block=None):
        super().__init__(if_token)
        self.condition = condition
        self.true_block = true_block # list of statements
        self.else_block = else_block # list of statements

    def __repr__(self):
        return f"IfStatement(cond={self.condition}, true_block={len(self.true_block)} stmts, else_block={len(self.else_block) if self.else_block else 0} stmts)"

class WhileLoop(Statement):
    def __init__(self, while_token, condition, body):
        super().__init__(while_token)
        self.condition = condition
        self.body = body # list of statements

    def __repr__(self):
        return f"WhileLoop(cond={self.condition}, body={len(self.body)} stmts)"

class ForLoop(Statement):
    def __init__(self, for_token, init, condition, increment, body):
        super().__init__(for_token)
        self.init = init # Statement (e.g., VarDecl or Assignment)
        self.condition = condition # Expression
        self.increment = increment # Statement (e.g., Assignment or FunctionCall)
        self.body = body # list of statements

    def __repr__(self):
        return f"ForLoop(init={self.init}, cond={self.condition}, inc={self.increment}, body={len(self.body)} stmts)"

class FunctionDecl(Statement):
    def __init__(self, return_type_token, id_token, params, body):
        super().__init__(return_type_token)
        self.return_type = return_type_token.value
        self.name = id_token.value
        self.parameters = params # list of (type_token, id_token) tuples
        self.body = body # list of statements

    def __repr__(self):
        return f"FunctionDecl(name={self.name}, return_type={self.return_type}, params={len(self.parameters)}, body={len(self.body)} stmts)"

class FunctionCall(Expression):
    def __init__(self, id_token, args):
        super().__init__(id_token)
        self.name = id_token.value
        self.arguments = args # list of Expressions

    def __repr__(self):
        return f"FunctionCall(name={self.name}, args={len(self.arguments)})"

class ReturnStatement(Statement):
    def __init__(self, return_token, expr=None):
        super().__init__(return_token)
        self.expression = expr

    def __repr__(self):
        return f"ReturnStatement(expr={self.expression})"

class PrintStatement(Statement):
    def __init__(self, print_token, expr):
        super().__init__(print_token)
        self.expression = expr

    def __repr__(self):
        return f"PrintStatement(expr={self.expression})"

# --- Parser ---
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_idx = 0
        self.current_token = self.tokens[0]

    def _advance(self):
        self.current_token_idx += 1
        self.current_token = self.tokens[self.current_token_idx]

    def _eat(self, *token_types):
        if self.current_token.type in token_types:
            token = self.current_token
            self._advance()
            return token
        else:
            expected = ", ".join(token_types)
            raise SyntaxError(
                f"Expected one of {expected}, got {self.current_token.type}",
                self.current_token.line, self.current_token.column
            )

    def parse(self):
        return self._program()

    def _program(self):
        statements = []
        while self.current_token.type != 'EOF':
            statements.append(self._declaration_or_statement())
        return Program(statements)

    def _declaration_or_statement(self):
        if self.current_token.type == 'TYPE':
            # Could be a variable declaration or function declaration
            # Look ahead to distinguish: TYPE IDENTIFIER LPAREN for function
            # TYPE IDENTIFIER SEMICOLON or OP_ASSIGN for variable
            if self.current_token_idx + 2 < len(self.tokens):
                peek_token = self.tokens[self.current_token_idx + 2]
                if peek_token.type == 'LPAREN':
                    return self._function_declaration()
            return self._variable_declaration()
        else:
            return self._statement()

    def _variable_declaration(self):
        type_token = self._eat('TYPE')
        id_token = self._eat('IDENTIFIER')
        expr = None
        if self.current_token.type == 'OP_ASSIGN':
            self._eat('OP_ASSIGN')
            expr = self._expression()
        self._eat('SEMICOLON')
        return VariableDecl(type_token, id_token, expr)

    def _function_declaration(self):
        return_type_token = self._eat('TYPE')
        id_token = self._eat('IDENTIFIER')
        self._eat('LPAREN')
        params = []
        if self.current_token.type == 'TYPE': # Check if there are parameters
            while True:
                param_type = self._eat('TYPE')
                param_id = self._eat('IDENTIFIER')
                params.append((param_type, param_id))
                if self.current_token.type == 'COMMA':
                    self._eat('COMMA')
                else:
                    break
        self._eat('RPAREN')
        self._eat('LBRACE')
        body = self._block_statements()
        self._eat('RBRACE')
        return FunctionDecl(return_type_token, id_token, params, body)

    def _statement(self):
        if self.current_token.type == 'IF':
            return self._if_statement()
        elif self.current_token.type == 'WHILE':
            return self._while_loop()
        elif self.current_token.type == 'FOR':
            return self._for_loop()
        elif self.current_token.type == 'PRINT':
            return self._print_statement()
        elif self.current_token.type == 'RETURN':
            return self._return_statement()
        elif self.current_token.type == 'IDENTIFIER':
            # Could be assignment or function call
            peek_token = self.tokens[self.current_token_idx + 1]
            if peek_token.type == 'OP_ASSIGN':
                return self._assignment_statement()
            elif peek_token.type == 'LPAREN':
                # Function call as a statement
                func_call = self._function_call()
                self._eat('SEMICOLON')
                return func_call
            else:
                raise SyntaxError(
                    f"Unexpected token after identifier: {peek_token.type}",
                    peek_token.line, peek_token.column
                )
        elif self.current_token.type == 'LBRACE': # Anonymous block scope
            self._eat('LBRACE')
            statements = self._block_statements()
            self._eat('RBRACE')
            return Program(statements) # Treat as a mini-program block for execution
        else:
            raise SyntaxError(
                f"Unexpected token: {self.current_token.type}",
                self.current_token.line, self.current_token.column
            )

    def _block_statements(self):
        statements = []
        while self.current_token.type != 'RBRACE' and self.current_token.type != 'EOF':
            statements.append(self._declaration_or_statement())
        return statements

    def _if_statement(self):
        if_token = self._eat('IF')
        self._eat('LPAREN')
        condition = self._expression()
        self._eat('RPAREN')
        self._eat('LBRACE')
        true_block = self._block_statements()
        self._eat('RBRACE')
        else_block = None
        if self.current_token.type == 'ELSE':
            self._eat('ELSE')
            self._eat('LBRACE')
            else_block = self._block_statements()
            self._eat('RBRACE')
        return IfStatement(if_token, condition, true_block, else_block)

    def _while_loop(self):
        while_token = self._eat('WHILE')
        self._eat('LPAREN')
        condition = self._expression()
        self._eat('RPAREN')
        self._eat('LBRACE')
        body = self._block_statements()
        self._eat('RBRACE')
        return WhileLoop(while_token, condition, body)

    def _for_loop(self):
        for_token = self._eat('FOR')
        self._eat('LPAREN')
        init = None
        if self.current_token.type != 'SEMICOLON':
            if self.current_token.type == 'TYPE':
                init = self._variable_declaration() # This eats semicolon
            elif self.current_token.type == 'IDENTIFIER':
                init = self._assignment_statement(expect_semicolon=True) # This eats semicolon
            else:
                raise SyntaxError("Expected variable declaration or assignment in for loop initialization",
                                  self.current_token.line, self.current_token.column)
        else:
            self._eat('SEMICOLON') # If init is empty, still need to eat semicolon

        condition = self._expression()
        self._eat('SEMICOLON')

        increment = None
        if self.current_token.type != 'RPAREN':
            if self.current_token.type == 'IDENTIFIER':
                peek_token = self.tokens[self.current_token_idx + 1]
                if peek_token.type == 'OP_ASSIGN':
                    increment = self._assignment_statement(expect_semicolon=False) # Don't eat semicolon
                elif peek_token.type == 'LPAREN':
                    increment = self._function_call() # Function call as increment
                else:
                    raise SyntaxError("Expected assignment or function call in for loop increment",
                                      self.current_token.line, self.current_token.column)
            else:
                raise SyntaxError("Expected assignment or function call in for loop increment",
                                  self.current_token.line, self.current_token.column)
        self._eat('RPAREN')
        self._eat('LBRACE')
        body = self._block_statements()
        self._eat('RBRACE')
        return ForLoop(for_token, init, condition, increment, body)

    def _print_statement(self):
        print_token = self._eat('PRINT')
        self._eat('LPAREN')
        expr = self._expression()
        self._eat('RPAREN')
        self._eat('SEMICOLON')
        return PrintStatement(print_token, expr)

    def _return_statement(self):
        return_token = self._eat('RETURN')
        expr = None
        if self.current_token.type != 'SEMICOLON':
            expr = self._expression()
        self._eat('SEMICOLON')
        return ReturnStatement(return_token, expr)

    def _assignment_statement(self, expect_semicolon=True):
        id_token = self._eat('IDENTIFIER')
        self._eat('OP_ASSIGN')
        expr = self._expression()
        if expect_semicolon:
            self._eat('SEMICOLON')
        return Assignment(id_token, expr)

    def _expression(self):
        return self._logical_or_expression()

    def _logical_or_expression(self):
        node = self._logical_and_expression()
        while self.current_token.type == 'OP_OR':
            op_token = self._eat('OP_OR')
            node = BinaryOp(node, op_token, self._logical_and_expression())
        return node

    def _logical_and_expression(self):
        node = self._equality_expression()
        while self.current_token.type == 'OP_AND':
            op_token = self._eat('OP_AND')
            node = BinaryOp(node, op_token, self._equality_expression())
        return node

    def _equality_expression(self):
        node = self._comparison_expression()
        while self.current_token.type in ('OP_EQ', 'OP_NE'):
            op_token = self._eat('OP_EQ', 'OP_NE')
            node = BinaryOp(node, op_token, self._comparison_expression())
        return node

    def _comparison_expression(self):
        node = self._additive_expression()
        while self.current_token.type in ('OP_LT', 'OP_GT', 'OP_LE', 'OP_GE'):
            op_token = self._eat('OP_LT', 'OP_GT', 'OP_LE', 'OP_GE')
            node = BinaryOp(node, op_token, self._additive_expression())
        return node

    def _additive_expression(self):
        node = self._multiplicative_expression()
        while self.current_token.type in ('OP_PLUS', 'OP_MINUS'):
            op_token = self._eat('OP_PLUS', 'OP_MINUS')
            node = BinaryOp(node, op_token, self._multiplicative_expression())
        return node

    def _multiplicative_expression(self):
        node = self._unary_expression()
        while self.current_token.type in ('OP_MUL', 'OP_DIV', 'OP_MOD'):
            op_token = self._eat('OP_MUL', 'OP_DIV', 'OP_MOD')
            node = BinaryOp(node, op_token, self._unary_expression())
        return node

    def _unary_expression(self):
        if self.current_token.type in ('OP_MINUS', 'OP_NOT'):
            op_token = self._eat('OP_MINUS', 'OP_NOT')
            return UnaryOp(op_token, self._unary_expression())
        return self._primary_expression()

    def _primary_expression(self):
        token = self.current_token
        if token.type == 'INTEGER':
            self._eat('INTEGER')
            return Literal(token, int(token.value), 'int')
        elif token.type == 'BOOLEAN':
            self._eat('BOOLEAN')
            return Literal(token, token.value == 'true', 'bool')
        elif token.type == 'STRING':
            self._eat('STRING')
            # Remove quotes and handle escaped characters
            value = token.value[1:-1].replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
            return Literal(token, value, 'string')
        elif token.type == 'IDENTIFIER':
            id_token = self._eat('IDENTIFIER')
            if self.current_token.type == 'LPAREN': # Function call
                return self._function_call(id_token=id_token)
            return Identifier(id_token)
        elif token.type == 'LPAREN':
            self._eat('LPAREN')
            expr = self._expression()
            self._eat('RPAREN')
            return expr
        elif token.type in ('READ_INT', 'READ_BOOL', 'READ_STR'):
            return self._builtin_read_call()
        else:
            raise SyntaxError(
                f"Unexpected token in expression: {token.type}",
                token.line, token.column
            )

    def _function_call(self, id_token=None):
        if id_token is None:
            id_token = self._eat('IDENTIFIER') # For cases like `print(func())`
        self._eat('LPAREN')
        args = []
        if self.current_token.type != 'RPAREN':
            while True:
                args.append(self._expression())
                if self.current_token.type == 'COMMA':
                    self._eat('COMMA')
                else:
                    break
        self._eat('RPAREN')
        return FunctionCall(id_token, args)

    def _builtin_read_call(self):
        token = self.current_token
        if token.type == 'READ_INT':
            self._eat('READ_INT')
            self._eat('LPAREN')
            self._eat('RPAREN')
            return FunctionCall(token, [])
        elif token.type == 'READ_BOOL':
            self._eat('READ_BOOL')
            self._eat('LPAREN')
            self._eat('RPAREN')
            return FunctionCall(token, [])
        elif token.type == 'READ_STR':
            self._eat('READ_STR')
            self._eat('LPAREN')
            self._eat('RPAREN')
            return FunctionCall(token, [])
        else:
            raise SyntaxError(
                f"Unexpected token for built-in read call: {token.type}",
                token.line, token.column
            )

# --- Type Checker (Skeleton) ---
class TypeChecker:
    def __init__(self):
        self.symbol_table = {} # Global scope for now
        self.current_function_return_type = None

    def check(self, ast):
        # This is a placeholder for a full static type checker.
        # The interpreter performs dynamic type checks during execution.
        pass

# --- Interpreter ---
class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def define(self, name, type_name, value=None):
        if name in self.symbols:
            raise RuntimeError(f"Variable '{name}' already defined in this scope.")
        self.symbols[name] = {'type': type_name, 'value': value}

    def assign(self, name, value, node_for_error=None):
        scope = self._resolve(name)
        if scope:
            # Type check assignment (basic)
            expected_type = scope[name]['type']
            actual_type = self._get_runtime_type(value)
            if expected_type != 'void' and expected_type != actual_type: # void can't be assigned
                raise RuntimeError(f"Type mismatch for variable '{name}': expected {expected_type}, got {actual_type}",
                                   node_for_error.line, node_for_error.column)
            scope[name]['value'] = value
        else:
            raise RuntimeError(f"Undefined variable '{name}'", node_for_error.line, node_for_error.column)

    def get(self, name, node_for_error=None):
        scope = self._resolve(name)
        if scope:
            return scope[name]['value']
        raise RuntimeError(f"Undefined variable '{name}'", node_for_error.line, node_for_error.column)

    def _resolve(self, name):
        if name in self.symbols:
            return self.symbols
        if self.parent:
            return self.parent._resolve(name)
        return None # Not found

    def _get_runtime_type(self, value):
        if isinstance(value, int):
            return 'int'
        elif isinstance(value, bool):
            return 'bool'
        elif isinstance(value, str):
            return 'string'
        elif value is None:
            return 'void' # For functions that return nothing or uninitialized vars
        return 'unknown' # Should not happen with our basic types

class Interpreter:
    def __init__(self, program_ast, inputs=None):
        self.program_ast = program_ast
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.output_buffer = []
        self.input_queue = deque(inputs if inputs is not None else [])
        self.functions = {} # Stores FunctionDecl nodes

        # Built-in functions are handled specially, not defined in symbol table
        # as they don't have a 'value' in the same way variables do.
        # Their existence is checked in _call_function.

    def _enter_scope(self):
        self.current_scope = SymbolTable(self.current_scope)

    def _exit_scope(self):
        self.current_scope = self.current_scope.parent

    def interpret(self):
        # First pass: register function declarations
        for stmt in self.program_ast.statements:
            if isinstance(stmt, FunctionDecl):
                if stmt.name in self.functions:
                    raise RuntimeError(f"Function '{stmt.name}' already defined.", stmt.line, stmt.column)
                self.functions[stmt.name] = stmt

        # Execute global statements (excluding function declarations)
        for stmt in self.program_ast.statements:
            if not isinstance(stmt, FunctionDecl):
                self._execute_statement(stmt)
        return "".join(self.output_buffer)

    def _execute_statement(self, node):
        if isinstance(node, VariableDecl):
            value = None
            if node.expression:
                value = self._evaluate_expression(node.expression)
                # Basic type check during declaration with assignment
                if node.var_type == 'int' and not isinstance(value, int):
                    raise RuntimeError(f"Type mismatch: Expected int, got {type(value).__name__}", node.line, node.column)
                if node.var_type == 'bool' and not isinstance(value, bool):
                    raise RuntimeError(f"Type mismatch: Expected bool, got {type(value).__name__}", node.line, node.column)
                if node.var_type == 'string' and not isinstance(value, str):
                    raise RuntimeError(f"Type mismatch: Expected string, got {type(value).__name__}", node.line, node.column)
            self.current_scope.define(node.name, node.var_type, value)
        elif isinstance(node, Assignment):
            value = self._evaluate_expression(node.expression)
            self.current_scope.assign(node.name, value, node)
        elif isinstance(node, PrintStatement):
            value = self._evaluate_expression(node.expression)
            self.output_buffer.append(str(value).lower() if isinstance(value, bool) else str(value) + "\n") # 'true'/'false' for bools
        elif isinstance(node, IfStatement):
            condition_value = self._evaluate_expression(node.condition)
            if not isinstance(condition_value, bool):
                raise RuntimeError("If condition must evaluate to a boolean.", node.line, node.column)
            self._enter_scope()
            if condition_value:
                for stmt in node.true_block:
                    self._execute_statement(stmt)
            elif node.else_block:
                for stmt in node.else_block:
                    self._execute_statement(stmt)
            self._exit_scope()
        elif isinstance(node, WhileLoop):
            self._enter_scope()
            while True:
                condition_value = self._evaluate_expression(node.condition)
                if not isinstance(condition_value, bool):
                    raise RuntimeError("While condition must evaluate to a boolean.", node.line, node.column)
                if not condition_value:
                    break
                for stmt in node.body:
                    self._execute_statement(stmt)
            self._exit_scope()
        elif isinstance(node, ForLoop):
            self._enter_scope()
            if node.init:
                self._execute_statement(node.init)
            while True:
                condition_value = self._evaluate_expression(node.condition)
                if not isinstance(condition_value, bool):
                    raise RuntimeError("For loop condition must evaluate to a boolean.", node.line, node.column)
                if not condition_value:
                    break
                for stmt in node.body:
                    self._execute_statement(stmt)
                if node.increment:
                    # For increment, it's an expression statement, so we just evaluate it.
                    # It could be an assignment or a function call.
                    if isinstance(node.increment, Assignment):
                        self._execute_statement(node.increment)
                    elif isinstance(node.increment, FunctionCall):
                        self._evaluate_expression(node.increment) # Execute for side effects
                    else:
                        raise RuntimeError("Invalid increment statement in for loop.", node.increment.line, node.increment.column)
            self._exit_scope()
        elif isinstance(node, FunctionCall):
            # If a function call is a statement, we just evaluate it for side effects
            self._evaluate_expression(node)
        elif isinstance(node, ReturnStatement):
            if node.expression:
                value = self._evaluate_expression(node.expression)
                raise ReturnValue(value)
            else:
                raise ReturnValue(None) # For void functions
        elif isinstance(node, Program): # For anonymous blocks { ... }
            self._enter_scope()
            for stmt in node.statements:
                self._execute_statement(stmt)
            self._exit_scope()
        else:
            raise RuntimeError(f"Unknown statement type: {type(node).__name__}", node.line, node.column)


    def _evaluate_expression(self, node):
        if isinstance(node, Literal):
            return node.value
        elif isinstance(node, Identifier):
            return self.current_scope.get(node.name, node)
        elif isinstance(node, BinaryOp):
            left_val = self._evaluate_expression(node.left)
            right_val = self._evaluate_expression(node.right)

            op = node.op
            if op == '+':
                if isinstance(left_val, int) and isinstance(right_val, int):
                    return left_val + right_val
                if isinstance(left_val, str) and isinstance(right_val, str):
                    return left_val + right_val
                raise RuntimeError(f"Unsupported operand types for +: {type(left_val).__name__} and {type(right_val).__name__}", node.line, node.column)
            elif op == '-':
                if isinstance(left_val, int) and isinstance(right_val, int):
                    return left_val - right_val
                raise RuntimeError(f"Unsupported operand types for -: {type(left_val).__name__} and {type(right_val).__name__}", node.line, node.column)
            elif op == '*':
                if isinstance(left_val, int) and isinstance(right_val, int):
                    return left_val * right_val
                raise RuntimeError(f"Unsupported operand types for *: {type(left_val).__name__} and {type(right_val).__name__}", node.line, node.column)
            elif op == '/':
                if isinstance(left_val, int) and isinstance(right_val, int):
                    if right_val == 0:
                        raise RuntimeError("Division by zero", node.line, node.column)
                    return left_val // right_val # Integer division
                raise RuntimeError(f"Unsupported operand types for /: {type(left_val).__name__} and {type(right_val).__name__}", node.line, node.column)
            elif op == '%':
                if isinstance(left_val, int) and isinstance(right_val, int):
                    if right_val == 0:
                        raise RuntimeError("Modulo by zero", node.line, node.column)
                    return left_val % right_val
                raise RuntimeError(f"Unsupported operand types for %: {type(left_val).__name__} and {type(right_val).__name__}", node.line, node.column)
            elif op in ('==', '!=', '<', '>', '<=', '>='):
                # Comparison operators work across types if Python allows, but we might want stricter rules.
                # For now, allow Python's default comparison.
                if op == '==': return left_val == right_val
                if op == '!=': return left_val != right_val
                if op == '<':  return left_val < right_val
                if op == '>':  return left_val > right_val
                if op == '<=': return left_val <= right_val
                if op == '>=': return left_val >= right_val
            elif op == '&&':
                if isinstance(left_val, bool) and isinstance(right_val, bool):
                    return left_val and right_val
                raise RuntimeError("Operands for '&&' must be booleans.", node.line, node.column)
            elif op == '||':
                if isinstance(left_val, bool) and isinstance(right_val, bool):
                    return left_val or right_val
                raise RuntimeError("Operands for '||' must be booleans.", node.line, node.column)
            else:
                raise RuntimeError(f"Unknown binary operator: {op}", node.line, node.column)
        elif isinstance(node, UnaryOp):
            right_val = self._evaluate_expression(node.right)
            op = node.op
            if op == '-':
                if isinstance(right_val, int):
                    return -right_val
                raise RuntimeError(f"Unsupported operand type for unary -: {type(right_val).__name__}", node.line, node.column)
            elif op == '!':
                if isinstance(right_val, bool):
                    return not right_val
                raise RuntimeError(f"Unsupported operand type for unary !: {type(right_val).__name__}", node.line, node.column)
            else:
                raise RuntimeError(f"Unknown unary operator: {op}", node.line, node.column)
        elif isinstance(node, FunctionCall):
            return self._call_function(node)
        else:
            raise RuntimeError(f"Unknown expression type: {type(node).__name__}", node.line, node.column)

    def _call_function(self, node):
        func_name = node.name
        args = [self._evaluate_expression(arg_expr) for arg_expr in node.arguments]

        # Handle built-in functions
        if func_name == 'print':
            if len(args) != 1:
                raise RuntimeError("print() expects exactly one argument.", node.line, node.column)
            self.output_buffer.append(str(args[0]).lower() if isinstance(args[0], bool) else str(args[0]) + "\n")
            return None # print returns void
        elif func_name == 'read_int':
            if len(args) != 0:
                raise RuntimeError("read_int() expects no arguments.", node.line, node.column)
            if not self.input_queue:
                raise RuntimeError("No input provided for read_int().", node.line, node.column)
            val = self.input_queue.popleft()
            if not isinstance(val, int):
                raise RuntimeError(f"Expected int input for read_int(), got {type(val).__name__}.", node.line, node.column)
            return val
        elif func_name == 'read_bool':
            if len(args) != 0:
                raise RuntimeError("read_bool() expects no arguments.", node.line, node.column)
            if not self.input_queue:
                raise RuntimeError("No input provided for read_bool().", node.line, node.column)
            val = self.input_queue.popleft()
            if not isinstance(val, bool):
                raise RuntimeError(f"Expected bool input for read_bool(), got {type(val).__name__}.", node.line, node.column)
            return val
        elif func_name == 'read_str':
            if len(args) != 0:
                raise RuntimeError("read_str() expects no arguments.", node.line, node.column)
            if not self.input_queue:
                raise RuntimeError("No input provided for read_str().", node.line, node.column)
            val = self.input_queue.popleft()
            if not isinstance(val, str):
                raise RuntimeError(f"Expected string input for read_str(), got {type(val).__name__}.", node.line, node.column)
            return val

        # Handle user-defined functions
        if func_name not in self.functions:
            raise RuntimeError(f"Undefined function '{func_name}'", node.line, node.column)

        func_decl = self.functions[func_name]
        if len(args) != len(func_decl.parameters):
            raise RuntimeError(f"Function '{func_name}' expects {len(func_decl.parameters)} arguments, but got {len(args)}.", node.line, node.column)

        self._enter_scope()
        # Bind parameters to arguments
        for (param_type_token, param_id_token), arg_value in zip(func_decl.parameters, args):
            # Basic type check for parameters
            expected_type = param_type_token.value
            actual_type = self.current_scope._get_runtime_type(arg_value)
            if expected_type != actual_type:
                raise RuntimeError(f"Type mismatch for parameter '{param_id_token.value}' in function '{func_name}': expected {expected_type}, got {actual_type}.", param_id_token.line, param_id_token.column)
            self.current_scope.define(param_id_token.value, expected_type, arg_value)

        return_value = None
        try:
            for stmt in func_decl.body:
                self._execute_statement(stmt)
        except ReturnValue as e:
            return_value = e.value
        finally:
            self._exit_scope()

        # Check return type (basic)
        expected_return_type = func_decl.return_type
        actual_return_type = self.current_scope._get_runtime_type(return_value)

        if expected_return_type == 'void' and return_value is not None:
            raise RuntimeError(f"Function '{func_name}' declared as 'void' but returned a value.", node.line, node.column)
        if expected_return_type != 'void' and return_value is None:
             raise RuntimeError(f"Function '{func_name}' declared to return '{expected_return_type}' but returned nothing.", node.line, node.column)
        if expected_return_type != 'void' and expected_return_type != actual_return_type:
            raise RuntimeError(f"Function '{func_name}' expected to return '{expected_return_type}', but returned '{actual_return_type}'.", node.line, node.column)

        return return_value

class ReturnValue(Exception):
    """Special exception to propagate return values from functions."""
    def __init__(self, value):
        self.value = value

# --- Main Interpreter Entry Point ---
def interpreter_main(program_code: str, inputs: list = None) -> str:
    """
    Main entry point for the C-like language interpreter.

    Args:
        program_code (str): The multi-line text of the program.
        inputs (list, optional): A list of inputs for read_int/bool/str calls.
                                 Defaults to None, meaning real stdin will be used.

    Returns:
        str: The accumulated output of the program.
    """
    try:
        lexer = Lexer(program_code)
        tokens = lexer.get_tokens()

        parser = Parser(tokens)
        ast = parser.parse()

        # Type checking (currently a skeleton)
        type_checker = TypeChecker()
        type_checker.check(ast)

        interpreter = Interpreter(ast, inputs)
        output = interpreter.interpret()
        return output
    except InterpreterError as e:
        return f"Error: {e}\n"
    except Exception as e:
        # Catch any unexpected Python errors during interpretation
        return f"Unexpected Interpreter Error: {e}\n"

# --- Test Programs ---
TEST_PROGRAMS = [
    {
        "code": """
            int main() {
                print(10);
                return 0;
            }
        """,
        "description": "Basic print of an integer literal.",
        "expected_output": "10\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 5;
                int y = 10;
                print(x + y);
                return 0;
            }
        """,
        "description": "Variable declaration, assignment, and arithmetic.",
        "expected_output": "15\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                if (x > 5) {
                    print("x is greater than 5");
                } else {
                    print("x is not greater than 5");
                }
                return 0;
            }
        """,
        "description": "If-else statement with string literal.",
        "expected_output": "x is greater than 5\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 3;
                if (x == 5) {
                    print("x is 5");
                } else if (x < 5) {
                    print("x is less than 5");
                } else {
                    print("x is greater than 5");
                }
                return 0;
            }
        """,
        "description": "If-else if-else chain.",
        "expected_output": "x is less than 5\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int i = 0;
                while (i < 3) {
                    print(i);
                    i = i + 1;
                }
                return 0;
            }
        """,
        "description": "While loop.",
        "expected_output": "0\n1\n2\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                for (int i = 0; i < 3; i = i + 1) {
                    print(i);
                }
                return 0;
            }
        """,
        "description": "For loop.",
        "expected_output": "0\n1\n2\n",
        "inputs": []
    },
    {
        "code": """
            int add(int a, int b) {
                return a + b;
            }
            int main() {
                int result = add(5, 7);
                print(result);
                return 0;
            }
        """,
        "description": "Function declaration and call.",
        "expected_output": "12\n",
        "inputs": []
    },
    {
        "code": """
            int factorial(int n) {
                if (n == 0) {
                    return 1;
                } else {
                    return n * factorial(n - 1);
                }
            }
            int main() {
                print(factorial(4)); // 4 * 3 * 2 * 1 = 24
                return 0;
            }
        """,
        "description": "Recursion.",
        "expected_output": "24\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                print(read_int() + read_int());
                return 0;
            }
        """,
        "description": "Read integers from input.",
        "expected_output": "15\n",
        "inputs": [5, 10]
    },
    {
        "code": """
            int main() {
                bool a = read_bool();
                bool b = read_bool();
                if (a && b) {
                    print("Both true");
                } else {
                    print("At least one false");
                }
                return 0;
            }
        """,
        "description": "Read booleans and logical AND.",
        "expected_output": "At least one false\n",
        "inputs": [True, False]
    },
    {
        "code": """
            int main() {
                string name = read_str();
                print("Hello, " + name + "!");
                return 0;
            }
        """,
        "description": "Read string and string concatenation.",
        "expected_output": "Hello, World!\n",
        "inputs": ["World"]
    },
    {
        "code": """
            int calculate(int x, int y) {
                return (x * 2) + (y / 2);
            }
            int main() {
                print(calculate(5 + 1, 10 - 2)); // calculate(6, 8) -> (6*2) + (8/2) = 12 + 4 = 16
                return 0;
            }
        """,
        "description": "Complex expressions inside function call parameters.",
        "expected_output": "16\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int a = 10;
                int b = 3;
                print(a % b); // 1
                print(-a);    // -10
                bool c = true;
                print(!c);    // false
                return 0;
            }
        """,
        "description": "Modulo and unary operators.",
        "expected_output": "1\n-10\nfalse\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int i = 0;
                for (; i < 2; ) { // For loop with empty init and increment
                    print(i);
                    i = i + 1;
                }
                return 0;
            }
        """,
        "description": "For loop with empty initialization and increment parts.",
        "expected_output": "0\n1\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 0;
                if (x > 5 && y == 0) {
                    print("Condition true");
                }
                if (x < 5 || y == 0) {
                    print("Another condition true");
                }
                return 0;
            }
        """,
        "description": "Logical AND and OR operators.",
        "expected_output": "Condition true\nAnother condition true\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int i = 0;
                { // New scope
                    int i = 2; // Shadowing
                    print(i);
                }
                print(i); // Back to outer scope's i
                return 0;
            }
        """,
        "description": "Scope handling with block statements.",
        "expected_output": "2\n1\n",
        "inputs": []
    },
    {
        "code": """
            int sum_up_to(int n) {
                int sum = 0;
                for (int i = 1; i <= n; i = i + 1) {
                    sum = sum + i;
                }
                return sum;
            }
            int main() {
                print(sum_up_to(5)); // 1+2+3+4+5 = 15
                return 0;
            }
        """,
        "description": "Function with for loop.",
        "expected_output": "15\n",
        "inputs": []
    },
    {
        "code": """
            string greet(string name) {
                return "Hello, " + name;
            }
            int main() {
                print(greet("Alice"));
                return 0;
            }
        """,
        "description": "Function returning string.",
        "expected_output": "Hello, Alice\n",
        "inputs": []
    },
    {
        "code": """
            bool is_even(int n) {
                return n % 2 == 0;
            }
            int main() {
                print(is_even(4));
                print(is_even(7));
                return 0;
            }
        """,
        "description": "Function returning boolean.",
        "expected_output": "true\nfalse\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                // This program should produce a runtime error: division by zero
                int x = 10;
                int y = 0;
                print(x / y);
                return 0;
            }
        """,
        "description": "Runtime error: Division by zero.",
        "expected_output": "Error: Runtime Error: Division by zero at line 6, column 22\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                // This program should produce a syntax error: missing semicolon
                int x = 10
                print(x);
                return 0;
            }
        """,
        "description": "Syntax error: Missing semicolon.",
        "expected_output": "Error: Syntax Error: Expected one of SEMICOLON, got PRINT at line 5, column 17\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                x = "hello"; // Type mismatch
                print(x);
                return 0;
            }
        """,
        "description": "Runtime error: Type mismatch on assignment.",
        "expected_output": "Error: Runtime Error: Type mismatch for variable 'x': expected int, got string at line 5, column 17\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x;
                print(x); // Undefined variable
                return 0;
            }
        """,
        "description": "Runtime error: Undefined variable access.",
        "expected_output": "Error: Runtime Error: Undefined variable 'x' at line 5, column 23\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int x = 20; // Redeclaration
                print(x);
                return 0;
            }
        """,
        "description": "Runtime error: Variable redeclaration in same scope.",
        "expected_output": "Error: Runtime Error: Variable 'x' already defined in this scope. at line 5, column 17\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                print(10 + "hello"); // Type mismatch for +
                return 0;
            }
        """,
        "description": "Runtime error: Type mismatch for binary operation.",
        "expected_output": "Error: Runtime Error: Unsupported operand types for +: int and str at line 4, column 22\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                if (x) { // Non-boolean condition
                    print("true");
                }
                return 0;
            }
        """,
        "description": "Runtime error: Non-boolean condition in if.",
        "expected_output": "Error: Runtime Error: If condition must evaluate to a boolean. at line 5, column 20\n",
        "inputs": []
    },
    {
        "code": """
            int foo() {
                return; // Function declared int but returns nothing
            }
            int main() {
                foo();
                return 0;
            }
        """,
        "description": "Runtime error: Function declared int but returns nothing.",
        "expected_output": "Error: Runtime Error: Function 'foo' declared to return 'int' but returned nothing. at line 8, column 17\n",
        "inputs": []
    },
    {
        "code": """
            void bar() {
                return 1; // Function declared void but returns value
            }
            int main() {
                bar();
                return 0;
            }
        """,
        "description": "Runtime error: Function declared void but returns value.",
        "expected_output": "Error: Runtime Error: Function 'bar' declared as 'void' but returned a value. at line 8, column 17\n",
        "inputs": []
    },
    {
        "code": """
            int sum(int a, int b) {
                return a + b;
            }
            int main() {
                print(sum(1, "two")); // Type mismatch in function call argument
                return 0;
            }
        """,
        "description": "Runtime error: Type mismatch in function call argument.",
        "expected_output": "Error: Runtime Error: Type mismatch for parameter 'b' in function 'sum': expected int, got string. at line 2, column 32\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                x = x + 1;
                print(x);
                return 0;
            }
        """,
        "description": "Self-assignment with arithmetic.",
        "expected_output": "11\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                print(read_int());
                return 0;
            }
        """,
        "description": "Runtime error: No input for read_int.",
        "expected_output": "Error: Runtime Error: No input provided for read_int(). at line 4, column 23\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                print(read_int());
                return 0;
            }
        """,
        "description": "Runtime error: Wrong input type for read_int.",
        "expected_output": "Error: Runtime Error: Expected int input for read_int(), got str. at line 4, column 23\n",
        "inputs": ["hello"]
    },
    {
        "code": """
            int main() {
                int x = 10;
                /* Multi-line comment 
                * Another line
                */
                print(x);
                return 0;
            }
        """,
        "description": "Multi-line comments.",
        "expected_output": "10\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10; // Single-line comment
                print(x);
                return 0;
            }
        """,
        "description": "Single-line comments.",
        "expected_output": "10\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                string s = "Hello\\nWorld";
                print(s);
                return 0;
            }
        """,
        "description": "String with newline escape sequence.",
        "expected_output": "Hello\nWorld\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                string s = "Path: C:\\\\Users\\\\";
                print(s);
                return 0;
            }
        """,
        "description": "String with backslash escape sequence.",
        "expected_output": "Path: C:\\Users\\\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                string s = "Quote: \\"Hello\\"";
                print(s);
                return 0;
            }
        """,
        "description": "String with double quote escape sequence.",
        "expected_output": "Quote: \"Hello\"\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                int z = 30;
                if (x < y && y < z) {
                    print("Chain comparison true");
                }
                if (x > y || y < z) {
                    print("Mixed comparison true");
                }
                return 0;
            }
        """,
        "description": "Complex logical expressions.",
        "expected_output": "Chain comparison true\nMixed comparison true\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                for (x = 0; x < 2; x = x + 1) { // For loop with assignment as init
                    print(i); // This should be 'x'
                }
                return 0;
            }
        """,
        "description": "For loop with assignment in initialization (buggy test).",
        "expected_output": "Error: Runtime Error: Undefined variable 'i' at line 5, column 21\n",
        "inputs": []
    },
    {
        "code": """
            int get_val() { return 5; }
            int main() {
                int i = 0;
                for (i = 0; i < 2; i = get_val()) { // For loop with function call in increment
                    print(i);
                }
                return 0;
            }
        """,
        "description": "For loop with function call in increment.",
        "expected_output": "0\n5\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                if (true) {
                    print("True block");
                }
                if (false) {
                    print("False block");
                } else {
                    print("Else block");
                }
                return 0;
            }
        """,
        "description": "If statements with boolean literals.",
        "expected_output": "True block\nElse block\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                int z = 30;
                if (x < y) {
                    if (y < z) {
                        print("Nested if true");
                    }
                }
                return 0;
            }
        """,
        "description": "Nested if statements.",
        "expected_output": "Nested if true\n",
        "inputs": []
    },
    {
        "code": """
            int get_five() {
                return 5;
            }
            int main() {
                print(get_five());
                return 0;
            }
        """,
        "description": "Function call returning a value.",
        "expected_output": "5\n",
        "inputs": []
    },
    {
        "code": """
            void do_nothing() {
                // This function does nothing
            }
            int main() {
                do_nothing();
                print("Done");
                return 0;
            }
        """,
        "description": "Void function call.",
        "expected_output": "Done\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                print( (x + 5) * 2 ); // Parenthesized expression
                return 0;
            }
        """,
        "description": "Parenthesized expressions.",
        "expected_output": "30\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                print(true);
                print(false);
                return 0;
            }
        """,
        "description": "Printing boolean literals.",
        "expected_output": "true\nfalse\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                print(x == y);
                print(x != y);
                return 0;
            }
        """,
        "description": "Equality and inequality operators.",
        "expected_output": "false\ntrue\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 10;
                print(x == y);
                print(x != y);
                return 0;
            }
        """,
        "description": "Equality and inequality operators with equal values.",
        "expected_output": "true\nfalse\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 5;
                print(x > y);
                print(x < y);
                print(x >= y);
                print(x <= y);
                print(x >= 10);
                print(x <= 10);
                return 0;
            }
        """,
        "description": "Relational operators.",
        "expected_output": "true\nfalse\ntrue\nfalse\ntrue\ntrue\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 2;
                int z = 3;
                print(x / y * z); // 10 / 2 * 3 = 5 * 3 = 15
                print(x * y / z); // 10 * 2 / 3 = 20 / 3 = 6
                print(x + y * z); // 10 + 2 * 3 = 10 + 6 = 16
                return 0;
            }
        """,
        "description": "Operator precedence.",
        "expected_output": "15\n6\n16\n",
        "inputs": []
    },
]

# --- Test Runner ---
def run_tests():
    total_tests = len(TEST_PROGRAMS)
    passed_tests = 0
    results = []

    print(f"Running {total_tests} tests...")

    for i, test_case in enumerate(TEST_PROGRAMS):
        code = test_case["code"]
        description = test_case["description"]
        expected_output = test_case["expected_output"]
        inputs = test_case.get("inputs", [])

        actual_output = ""
        try:
            actual_output = interpreter_main(code, inputs)
            if actual_output == expected_output:
                status = "PASS"
                passed_tests += 1
            else:
                status = "FAIL"
        except Exception as e:
            status = "ERROR"
            actual_output = f"Interpreter crashed: {e}\n"

        results.append({"description": description, "status": status, "actual_output": actual_output, "expected_output": expected_output})

    print("\n--- Test Summary ---")
    for res in results:
        print(f"[{res['status']}] {res['description']}")
        if res['status'] != 'PASS':
            print(f"  Expected:\n{res['expected_output'].strip()}")
            print(f"  Actual:\n{res['actual_output'].strip()}")

    print(f"\nTotal Tests: {total_tests}, Passed: {passed_tests}, Failed: {total_tests - passed_tests}")
    return passed_tests == total_tests

# --- Command Line Interface ---
def main():
    parser = argparse.ArgumentParser(description="A C-like language interpreter.")
    parser.add_argument("file", nargs='?', help="Path to the program file to execute.")
    parser.add_argument("--test", action="store_true", help="Run embedded test suite.")
    parser.add_argument("--syntax", action="store_true", help="Print language syntax documentation.")

    args = parser.parse_args()

    if args.syntax:
        print(LANGUAGE_SPECIFICATION)
        sys.exit(0)

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    if args.file:
        try:
            with open(args.file, 'r') as f:
                program_code = f.read()
            output = interpreter_main(program_code)
            sys.stdout.write(output)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        except Exception as e:
            print(f"Error executing program: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()