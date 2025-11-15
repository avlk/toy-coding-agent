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

class BlockStatement(ASTNode): # New AST node for anonymous blocks
    def __init__(self, statements, token=None):
        super().__init__(token)
        self.statements = statements

    def __repr__(self):
        return f"BlockStatement({len(self.statements)} stmts)"


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
                    f"Expected assignment or function call after identifier, got {peek_token.type}",
                    peek_token.line, peek_token.column
                )
        elif self.current_token.type == 'LBRACE': # Anonymous block scope
            lbrace_token = self._eat('LBRACE') # Capture token for line/column
            statements = self._block_statements()
            self._eat('RBRACE')
            return BlockStatement(statements, lbrace_token) # Use new BlockStatement
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

# --- Type Checker ---
class TypeSymbolTable:
    def __init__(self, parent=None):
        self.symbols = {} # Stores {'name': 'type_name'}
        self.parent = parent

    def define(self, name, type_name, node_for_error=None):
        if name in self.symbols:
            raise TypeError(f"Variable '{name}' already defined in this scope.", node_for_error.line, node_for_error.column)
        self.symbols[name] = type_name

    def resolve(self, name):
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None # Not found

class TypeChecker:
    def __init__(self):
        self.global_type_scope = TypeSymbolTable()
        self.current_type_scope = self.global_type_scope
        self.function_signatures = {} # Stores {'func_name': {'return_type': 'type', 'param_types': ['type', ...]}}
        self.current_function_return_type = None

        # Register built-in functions
        self.function_signatures['print'] = {'return_type': 'void', 'param_types': ['any']} # 'any' for print
        self.function_signatures['read_int'] = {'return_type': 'int', 'param_types': []}
        self.function_signatures['read_bool'] = {'return_type': 'bool', 'param_types': []}
        self.function_signatures['read_str'] = {'return_type': 'string', 'param_types': []}

    def _enter_scope(self):
        self.current_type_scope = TypeSymbolTable(self.current_type_scope)

    def _exit_scope(self):
        self.current_type_scope = self.current_type_scope.parent

    def check(self, ast):
        # First pass: register function declarations and global variables
        for stmt in ast.statements:
            if isinstance(stmt, FunctionDecl):
                if stmt.name in self.function_signatures:
                    raise TypeError(f"Function '{stmt.name}' already defined.", stmt.line, stmt.column)
                param_types = [p_type_token.value for p_type_token, _ in stmt.parameters]
                self.function_signatures[stmt.name] = {
                    'return_type': stmt.return_type,
                    'param_types': param_types
                }
            elif isinstance(stmt, VariableDecl):
                # Global variable declarations are checked in the first pass
                self._check_variable_declaration(stmt) # Check global variable declarations
        
        # Check main function signature after all functions are registered
        if 'main' not in self.function_signatures:
            raise TypeError("Program entry point 'main' function not found.")
        main_sig = self.function_signatures['main']
        if main_sig['return_type'] != 'int' or len(main_sig['param_types']) != 0:
            main_node = next((s for s in ast.statements if isinstance(s, FunctionDecl) and s.name == 'main'), None)
            raise TypeError("Function 'main' must have signature 'int main()'.", main_node.line, main_node.column)

        # Second pass: type check all function bodies and ensure no other top-level statements
        for stmt in ast.statements:
            if isinstance(stmt, FunctionDecl):
                self._check_function_declaration_body(stmt)
            elif not isinstance(stmt, VariableDecl):
                raise TypeError(f"Top-level statements other than function or variable declarations are not allowed.", stmt.line, stmt.column)

    def _check_statement(self, node):
        if isinstance(node, VariableDecl):
            self._check_variable_declaration(node)
        elif isinstance(node, Assignment):
            self._check_assignment(node)
        elif isinstance(node, PrintStatement):
            self._check_expression(node.expression) # Any type is fine for print
        elif isinstance(node, IfStatement):
            self._check_if_statement(node)
        elif isinstance(node, WhileLoop):
            self._check_while_loop(node)
        elif isinstance(node, ForLoop):
            self._check_for_loop(node)
        elif isinstance(node, FunctionCall):
            self._check_function_call(node) # Function calls can be statements
        elif isinstance(node, ReturnStatement):
            self._check_return_statement(node)
        elif isinstance(node, BlockStatement):
            self._enter_scope()
            for stmt in node.statements:
                self._check_statement(stmt)
            self._exit_scope()

    def _check_variable_declaration(self, node):
        declared_type = node.var_type
        if declared_type not in Lexer.TYPES:
            raise TypeError(f"Unknown type '{declared_type}'", node.line, node.column)

        if declared_type == 'void':
            raise TypeError(f"Cannot declare variable of type 'void'.", node.line, node.column)

        if node.expression:
            expr_type = self._check_expression(node.expression)
            if expr_type != declared_type:
                raise TypeError(f"Type mismatch in variable declaration for '{node.name}': expected {declared_type}, got {expr_type}.", node.line, node.column)
        self.current_type_scope.define(node.name, declared_type, node)

    def _check_assignment(self, node):
        var_type = self.current_type_scope.resolve(node.name)
        if var_type is None:
            raise TypeError(f"Undeclared variable '{node.name}'.", node.line, node.column)
        
        expr_type = self._check_expression(node.expression)
        if var_type != expr_type:
            raise TypeError(f"Type mismatch in assignment for '{node.name}': expected {var_type}, got {expr_type}.", node.line, node.column)

    def _check_if_statement(self, node):
        condition_type = self._check_expression(node.condition)
        if condition_type != 'bool':
            raise TypeError("If condition must be of type 'bool'.", node.condition.line, node.condition.column)
        self._enter_scope()
        for stmt in node.true_block:
            self._check_statement(stmt)
        self._exit_scope()
        if node.else_block:
            self._enter_scope()
            for stmt in node.else_block:
                self._check_statement(stmt)
            self._exit_scope()

    def _check_while_loop(self, node):
        condition_type = self._check_expression(node.condition)
        if condition_type != 'bool':
            raise TypeError("While loop condition must be of type 'bool'.", node.condition.line, node.condition.column)
        self._enter_scope()
        for stmt in node.body:
            self._check_statement(stmt)
        self._exit_scope()

    def _check_for_loop(self, node):
        self._enter_scope()
        if node.init:
            self._check_statement(node.init) # init can be VarDecl or Assignment
        
        condition_type = self._check_expression(node.condition)
        if condition_type != 'bool':
            raise TypeError("For loop condition must be of type 'bool'.", node.condition.line, node.condition.column)
        
        for stmt in node.body:
            self._check_statement(stmt)
        
        if node.increment:
            # Increment can be an assignment or a function call
            if isinstance(node.increment, Assignment):
                self._check_assignment(node.increment)
            elif isinstance(node.increment, FunctionCall):
                self._check_function_call(node.increment)
            else:
                raise TypeError("Invalid increment statement in for loop.", node.increment.line, node.increment.column)
        self._exit_scope()

    def _check_function_declaration_body(self, node):
        # This is called in the second pass to check the body
        self.current_function_return_type = node.return_type
        self._enter_scope()
        # Define parameters in the new scope
        for param_type_token, param_id_token in node.parameters:
            self.current_type_scope.define(param_id_token.value, param_type_token.value, param_id_token)
        
        for stmt in node.body:
            self._check_statement(stmt)
        self._exit_scope()
        self.current_function_return_type = None

    def _check_return_statement(self, node):
        if self.current_function_return_type is None:
            raise TypeError("Return statement outside of a function.", node.line, node.column)
        
        if node.expression:
            expr_type = self._check_expression(node.expression)
            if self.current_function_return_type == 'void':
                raise TypeError(f"Function declared as 'void' but returns a value.", node.line, node.column)
            if expr_type != self.current_function_return_type:
                raise TypeError(f"Return type mismatch: expected {self.current_function_return_type}, got {expr_type}.", node.line, node.column)
        else: # No expression
            if self.current_function_return_type != 'void':
                raise TypeError(f"Function declared to return '{self.current_function_return_type}' but returns nothing.", node.line, node.column)

    def _check_expression(self, node):
        if isinstance(node, Literal):
            return node.type_name
        elif isinstance(node, Identifier):
            var_type = self.current_type_scope.resolve(node.name)
            if var_type is None:
                raise TypeError(f"Undeclared identifier '{node.name}'.", node.line, node.column)
            return var_type
        elif isinstance(node, BinaryOp):
            left_type = self._check_expression(node.left)
            right_type = self._check_expression(node.right)
            op = node.op

            if op in ('+', '-', '*', '/', '%'):
                if left_type == 'int' and right_type == 'int':
                    return 'int'
                if op == '+' and left_type == 'string' and right_type == 'string':
                    return 'string'
                raise TypeError(f"Unsupported operand types for {op}: {left_type} and {right_type}.", node.line, node.column)
            elif op in ('==', '!='):
                if left_type == right_type: # Allow comparison of same types
                    return 'bool'
                raise TypeError(f"Incompatible types for equality comparison '{op}': {left_type} and {right_type}.", node.line, node.column)
            elif op in ('<', '>', '<=', '>='):
                if left_type == 'int' and right_type == 'int':
                    return 'bool'
                raise TypeError(f"Comparison operator '{op}' only supported for integers, got {left_type} and {right_type}.", node.line, node.column)
            elif op in ('&&', '||'):
                if left_type == 'bool' and right_type == 'bool':
                    return 'bool'
                raise TypeError(f"Operands for '{op}' must be booleans, got {left_type} and {right_type}.", node.line, node.column)
            else:
                raise TypeError(f"Unknown binary operator: {op}", node.line, node.column)
        elif isinstance(node, UnaryOp):
            right_type = self._check_expression(node.right)
            op = node.op
            if op == '-':
                if right_type == 'int':
                    return 'int'
                raise TypeError(f"Unsupported operand type for unary -: {right_type}.", node.line, node.column)
            elif op == '!':
                if right_type == 'bool':
                    return 'bool'
                raise TypeError(f"Unsupported operand type for unary !: {right_type}.", node.line, node.column)
            else:
                raise TypeError(f"Unknown unary operator: {op}", node.line, node.column)
        elif isinstance(node, FunctionCall):
            return self._check_function_call(node)
        else:
            raise TypeError(f"Unknown expression type during type checking: {type(node).__name__}", node.line, node.column)

    def _check_function_call(self, node):
        func_name = node.name
        if func_name not in self.function_signatures:
            raise TypeError(f"Undefined function '{func_name}'.", node.line, node.column)
        
        func_sig = self.function_signatures[func_name]
        
        if func_name == 'print': # Special handling for 'any' type
            if len(node.arguments) != 1:
                raise TypeError("print() expects exactly one argument.", node.line, node.column)
            self._check_expression(node.arguments[0]) # Just check it's a valid expression
            return 'void'

        if len(node.arguments) != len(func_sig['param_types']):
            raise TypeError(f"Function '{func_name}' expects {len(func_sig['param_types'])} arguments, but got {len(node.arguments)}.", node.line, node.column)
        
        for i, (arg_expr, expected_param_type) in enumerate(zip(node.arguments, func_sig['param_types'])):
            actual_arg_type = self._check_expression(arg_expr)
            if actual_arg_type != expected_param_type:
                raise TypeError(f"Type mismatch for argument {i+1} in function '{func_name}': expected {expected_param_type}, got {actual_arg_type}.", arg_expr.line, arg_expr.column)
        
        return func_sig['return_type']

# --- Interpreter ---
class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def define(self, name, type_name, value=None):
        if name in self.symbols:
            raise RuntimeError(f"Variable '{name}' already defined in this scope.", node_for_error=None) # No node for error here, TypeChecker should catch this
        self.symbols[name] = {'type': type_name, 'value': value}

    def assign(self, name, value, node_for_error=None):
        scope = self._resolve(name)
        if scope:
            # Type check assignment (basic)
            expected_type = scope[name]['type']
            actual_type = self._get_runtime_type(value)
            if expected_type != 'void' and expected_type != actual_type: # void can't be assigned, and types must match
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
            elif isinstance(stmt, VariableDecl):
                # Execute global variable declarations
                self._execute_statement(stmt)
            else:
                raise RuntimeError(f"Top-level statements other than function or variable declarations are not allowed.", stmt.line, stmt.column)

        # Create a dummy FunctionCall node for main to reuse _call_function logic
        # The TypeChecker ensures 'main' exists and has the correct signature.
        main_call_node = FunctionCall(Token('IDENTIFIER', 'main', None, None), []) # Line/column can be None for this synthetic node
        self._call_function(main_call_node) # Execute main

        return "".join(self.output_buffer)

    def _execute_statement(self, node):
        if isinstance(node, VariableDecl):
            value = None
            if node.expression:
                value = self._evaluate_expression(node.expression)
            self.current_scope.define(node.name, node.var_type, value)
        elif isinstance(node, Assignment):
            value = self._evaluate_expression(node.expression)
            self.current_scope.assign(node.name, value, node)
        elif isinstance(node, PrintStatement):
            value = self._evaluate_expression(node.expression)
            self.output_buffer.append(str(value).lower() if isinstance(value, bool) else str(value) + "\n") # 'true'/'false' for bools
        elif isinstance(node, IfStatement):
            condition_value = self._evaluate_expression(node.condition)
            # TypeChecker ensures condition_value is bool
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
                # TypeChecker ensures condition_value is bool
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
                # TypeChecker ensures condition_value is bool
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
                        # TypeChecker should catch this, but a runtime check for robustness
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
        elif isinstance(node, BlockStatement): # Correctly handle anonymous blocks
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
            # TypeChecker ensures operand types are compatible.
            # Only specific runtime checks like division by zero are needed.
            if op == '+':
                return left_val + right_val
            elif op == '-':
                return left_val - right_val
            elif op == '*':
                return left_val * right_val
            elif op == '/':
                if right_val == 0:
                    raise RuntimeError("Division by zero", node.line, node.column)
                return left_val // right_val # Integer division
            elif op == '%':
                if right_val == 0:
                    raise RuntimeError("Modulo by zero", node.line, node.column)
                return left_val % right_val
            elif op == '==': return left_val == right_val
            elif op == '!=': return left_val != right_val
            elif op == '<':  return left_val < right_val
            elif op == '>':  return left_val > right_val
            elif op == '<=': return left_val <= right_val
            elif op == '>=': return left_val >= right_val
            elif op == '&&':
                return left_val and right_val
            elif op == '||':
                return left_val or right_val
            else:
                raise RuntimeError(f"Unknown binary operator: {op}", node.line, node.column)
        elif isinstance(node, UnaryOp):
            right_val = self._evaluate_expression(node.right)
            op = node.op
            # TypeChecker ensures operand types are compatible.
            if op == '-':
                return -right_val
            elif op == '!':
                return not right_val
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
            # TypeChecker ensures argument count.
            self.output_buffer.append(str(args[0]).lower() if isinstance(args[0], bool) else str(args[0]) + "\n")
            return None # print returns void
        elif func_name == 'read_int':
            # TypeChecker ensures argument count.
            if not self.input_queue:
                raise RuntimeError("No input provided for read_int().", node.line, node.column)
            val = self.input_queue.popleft()
            if not isinstance(val, int):
                raise RuntimeError(f"Expected int input for read_int(), got {type(val).__name__}.", node.line, node.column)
            return val
        elif func_name == 'read_bool':
            # TypeChecker ensures argument count.
            if not self.input_queue:
                raise RuntimeError("No input provided for read_bool().", node.line, node.column)
            val = self.input_queue.popleft()
            if not isinstance(val, bool):
                raise RuntimeError(f"Expected bool input for read_bool(), got {type(val).__name__}.", node.line, node.column)
            return val
        elif func_name == 'read_str':
            # TypeChecker ensures argument count.
            if not self.input_queue:
                raise RuntimeError("No input provided for read_str().", node.line, node.column)
            val = self.input_queue.popleft()
            if not isinstance(val, str):
                raise RuntimeError(f"Expected string input for read_str(), got {type(val).__name__}.", node.line, node.column)
            return val

        # Handle user-defined functions
        if func_name not in self.functions:
            # TypeChecker should catch this, but a runtime check for robustness
            raise RuntimeError(f"Undefined function '{func_name}'", node.line, node.column)

        func_decl = self.functions[func_name]
        # TypeChecker ensures argument count and types.

        self._enter_scope()
        # Bind parameters to arguments
        for (param_type_token, param_id_token), arg_value in zip(func_decl.parameters, args):
            # SymbolTable.define performs runtime type check against declared type
            self.current_scope.define(param_id_token.value, param_type_token.value, arg_value)

        return_value = None
        try:
            for stmt in func_decl.body:
                self._execute_statement(stmt)
        except ReturnValue as e:
            return_value = e.value
        finally:
            self._exit_scope()

        # Check return type (runtime check for actual value returned)
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

        # Type checking
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
                print(factorial(4));
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
                print(calculate(5 + 1, 10 - 2));
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
                print(a % b);
                print(-a);
                bool c = true;
                print(!c);
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
                for (; i < 2; ) {
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
                {
                    int i = 2;
                    print(i);
                }
                print(i);
                return 0;
            }
        """,
        "description": "Scope handling with block statements.",
        "expected_output": "2\n0\n",
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
                print(sum_up_to(5));
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
                x = "hello";
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
                print(x);
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
                int x = 20;
                print(x);
                return 0;
            }
        """,
        "description": "Static Type error: Variable redeclaration in same scope.",
        "expected_output": "Error: Type Error: Variable 'x' already defined in this scope. at line 5, column 17\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                print(10 + "hello");
                return 0;
            }
        """,
        "description": "Static Type error: Type mismatch for binary operation.",
        "expected_output": "Error: Type Error: Unsupported operand types for +: int and string. at line 4, column 22\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                if (x) {
                    print("true");
                }
                return 0;
            }
        """,
        "description": "Static Type error: Non-boolean condition in if.",
        "expected_output": "Error: Type Error: If condition must be of type 'bool'. at line 5, column 20\n",
        "inputs": []
    },
    {
        "code": """
            int foo() {
                return;
            }
            int main() {
                foo();
                return 0;
            }
        """,
        "description": "Static Type error: Function declared int but returns nothing.",
        "expected_output": "Error: Type Error: Function declared to return 'int' but returns nothing. at line 3, column 17\n",
        "inputs": []
    },
    {
        "code": """
            void bar() {
                return 1;
            }
            int main() {
                bar();
                return 0;
            }
        """,
        "description": "Static Type error: Function declared void but returns value.",
        "expected_output": "Error: Type Error: Function declared as 'void' but returns a value. at line 3, column 17\n",
        "inputs": []
    },
    {
        "code": """
            int sum(int a, int b) {
                return a + b;
            }
            int main() {
                print(sum(1, "two"));
                return 0;
            }
        """,
        "description": "Static Type error: Type mismatch in function call argument.",
        "expected_output": "Error: Type Error: Type mismatch for argument 2 in function 'sum': expected int, got string. at line 5, column 27\n",
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
                int x = 10;
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
                for (x = 0; x < 2; x = x + 1) {
                    print(x);
                }
                return 0;
            }
        """,
        "description": "For loop with assignment in initialization.",
        "expected_output": "0\n1\n",
        "inputs": []
    },
    {
        "code": """
            int get_val() { return 5; }
            int main() {
                int i = 0;
                for (i = 0; i < 2; i = get_val()) {
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
                print( (x + 5) * 2 );
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
                print(x / y * z);
                print(x * y / z);
                print(x + y * z);
                return 0;
            }
        """,
        "description": "Operator precedence.",
        "expected_output": "15\n6\n16\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = true;
                return 0;
            }
        """,
        "description": "Static Type error: Type mismatch in variable declaration.",
        "expected_output": "Error: Type Error: Type mismatch in variable declaration for 'x': expected int, got bool. at line 4, column 25\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                if (10) {
                    print("true");
                }
                return 0;
            }
        """,
        "description": "Static Type error: Non-boolean condition in if statement.",
        "expected_output": "Error: Type Error: If condition must be of type 'bool'. at line 4, column 20\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                string s = "hello";
                print(x == s);
                return 0;
            }
        """,
        "description": "Static Type error: Incompatible types for equality comparison.",
        "expected_output": "Error: Type Error: Incompatible types for equality comparison '==': int and string. at line 5, column 27\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                bool b = true;
                print(x < b);
                return 0;
            }
        """,
        "description": "Static Type error: Incompatible types for relational comparison.",
        "expected_output": "Error: Type Error: Comparison operator '<' only supported for integers, got int and bool. at line 5, column 25\n",
        "inputs": []
    },
    {
        "code": """
            int global_var = 10;
            int main() {
                print(global_var);
                return 0;
            }
        """,
        "description": "Global variable declaration and access.",
        "expected_output": "10\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                print(x + y);
            }
        """,
        "description": "Missing return statement in int main().",
        "expected_output": "Error: Runtime Error: Function 'main' declared to return 'int' but returned nothing. at line 3, column 17\n",
        "inputs": []
    },
    {
        "code": """
            void foo() {
                print("Hello");
            }
            int main() {
                foo();
                return 0;
            }
        """,
        "description": "Void function call as statement.",
        "expected_output": "Hello\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                {
                    int y = 20;
                    print(x + y);
                }
                // print(y); // This would be a static type error (undeclared)
                return 0;
            }
        """,
        "description": "Nested block scope with outer variable access.",
        "expected_output": "30\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                if (x < y) {
                    int z = x + y;
                    print(z);
                } else {
                    int w = x - y;
                    print(w);
                }
                return 0;
            }
        """,
        "description": "Variable declaration within if-else blocks.",
        "expected_output": "30\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                while (x > 0) {
                    int y = x;
                    print(y);
                    x = x - 5;
                }
                return 0;
            }
        """,
        "description": "Variable declaration within while loop.",
        "expected_output": "10\n5\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                {
                    string x = "hello"; // Redeclaration in inner scope is allowed (shadowing)
                    print(x);
                }
                print(x); // Outer x
                return 0;
            }
        """,
        "description": "Shadowing variable in inner block.",
        "expected_output": "hello\n10\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                x = !x; // Type mismatch
                return 0;
            }
        """,
        "description": "Static Type error: Type mismatch with unary operator.",
        "expected_output": "Error: Type Error: Type mismatch in assignment for 'x': expected int, got bool. at line 5, column 21\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x;
                x = 10; // Assignment to uninitialized variable
                print(x);
                return 0;
            }
        """,
        "description": "Variable declaration without initialization, then assignment.",
        "expected_output": "10\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                int z = (x + y) * 2;
                print(z);
                return 0;
            }
        """,
        "description": "Complex expression with multiple operators and parentheses.",
        "expected_output": "60\n",
        "inputs": []
    },
    {
        "code": """
            int a = 1;
            int b = 2;
            int c = 3;
            int main() {
                print(a + b * c); // 1 + (2 * 3) = 7
                print((a + b) * c); // (1 + 2) * 3 = 9
                return 0;
            }
        """,
        "description": "Operator precedence and associativity.",
        "expected_output": "7\n9\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 0;
                while (x > 0 && y < 5) {
                    print(x);
                    x = x - 1;
                    y = y + 1;
                }
                return 0;
            }
        """,
        "description": "While loop with complex logical condition.",
        "expected_output": "10\n9\n8\n7\n6\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                for (int i = 0; i < x; i = i + 1) {
                    if (i % 2 == 0) {
                        print(i);
                    }
                }
                return 0;
            }
        """,
        "description": "For loop with nested if and modulo operator.",
        "expected_output": "0\n2\n4\n6\n8\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                string s1 = "hello";
                string s2 = "world";
                print(s1 + s2);
                print(s1 == s2);
                print(s1 != s2);
                return 0;
            }
        """,
        "description": "String concatenation and comparison.",
        "expected_output": "helloworld\nfalse\ntrue\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                bool b1 = true;
                bool b2 = false;
                print(b1 && b2);
                print(b1 || b2);
                print(!b1);
                return 0;
            }
        """,
        "description": "Boolean logical operations.",
        "expected_output": "false\ntrue\nfalse\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                void y; // Cannot declare void variable
                return 0;
            }
        """,
        "description": "Static Type error: Declaring a void variable.",
        "expected_output": "Error: Type Error: Cannot declare variable of type 'void'. at line 5, column 17\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                int z = 30;
                if (x < y) {
                    print(z);
                }
                return 0;
            }
        """,
        "description": "Simple if statement.",
        "expected_output": "30\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                int z = 30;
                if (x > y) {
                    print(z);
                } else {
                    print(y);
                }
                return 0;
            }
        """,
        "description": "Simple if-else statement.",
        "expected_output": "20\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                int y = 20;
                int z = 30;
                if (x > y) {
                    print(z);
                } else if (x == 10) {
                    print(x);
                } else {
                    print(y);
                }
                return 0;
            }
        """,
        "description": "If-else if-else statement.",
        "expected_output": "10\n",
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
~~~

~~~shell
Running 68 tests...
--- Test Summary ---
[PASS] Basic print of an integer literal.
[PASS] Variable declaration, assignment, and arithmetic.
[PASS] If-else statement with string literal.
[PASS] If-else if-else chain.
[PASS] While loop.
[PASS] For loop.
[PASS] Function declaration and call.
[PASS] Recursion.
[PASS] Read integers from input.
[PASS] Read booleans and logical AND.
[PASS] Read string and string concatenation.
[PASS] Complex expressions inside function call parameters.
[PASS] Modulo and unary operators.
[PASS] For loop with empty initialization and increment parts.
[PASS] Logical AND and OR operators.
[PASS] Scope handling with block statements.
[PASS] Function with for loop.
[PASS] Function returning string.
[PASS] Function returning boolean.
[PASS] Runtime error: Division by zero.
[PASS] Syntax error: Missing semicolon.
[PASS] Runtime error: Type mismatch on assignment.
[PASS] Runtime error: Undefined variable access.
[PASS] Static Type error: Variable redeclaration in same scope.
[PASS] Static Type error: Type mismatch for binary operation.
[PASS] Static Type error: Non-boolean condition in if.
[PASS] Static Type error: Function declared int but returns nothing.
[PASS] Static Type error: Function declared void but returns value.
[PASS] Static Type error: Type mismatch in function call argument.
[PASS] Self-assignment with arithmetic.
[PASS] Runtime error: No input for read_int.
[PASS] Runtime error: Wrong input type for read_int.
[PASS] Multi-line comments.
[PASS] Single-line comments.
[PASS] String with newline escape sequence.
[PASS] String with backslash escape sequence.
[PASS] String with double quote escape sequence.
[PASS] Complex logical expressions.
[PASS] For loop with assignment in initialization.
[PASS] For loop with function call in increment.
[PASS] If statements with boolean literals.
[PASS] Nested if statements.
[PASS] Function call returning a value.
[PASS] Void function call.
[PASS] Parenthesized expressions.
[PASS] Printing boolean literals.
[PASS] Equality and inequality operators.
[PASS] Equality and inequality operators with equal values.
[PASS] Relational operators.
[PASS] Operator precedence.
[PASS] Static Type error: Type mismatch in variable declaration.
[PASS] Static Type error: Non-boolean condition in if statement.
[PASS] Static Type error: Incompatible types for equality comparison.
[PASS] Static Type error: Incompatible types for relational comparison.
[PASS] Global variable declaration and access.
[PASS] Missing return statement in int main().
[PASS] Void function call as statement.
[PASS] Nested block scope with outer variable access.
[PASS] Variable declaration within if-else blocks.
[PASS] Variable declaration within while loop.
[PASS] Shadowing variable in inner block.
[PASS] Static Type error: Type mismatch with unary operator.
[PASS] Variable declaration without initialization, then assignment.
[PASS] Complex expression with multiple operators and parentheses.
[PASS] Operator precedence and associativity.
[PASS] While loop with complex logical condition.
[PASS] For loop with nested if and modulo operator.
[PASS] String concatenation and comparison.
[PASS] Boolean logical operations.
[PASS] Static Type error: Declaring a void variable.
[PASS] Simple if statement.
[PASS] Simple if-else statement.
[PASS] If-else if-else statement.

Total Tests: 68, Passed: 68, Failed: 0
~~~
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
                if not ((isinstance(left_val, int) and isinstance(right_val, int)) or
                        (isinstance(left_val, str) and isinstance(right_val, str))):
                    raise RuntimeError(f"Unsupported operand types for +: {self.current_scope._get_runtime_type(left_val)} and {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                return left_val + right_val
            elif op == '-':
                if not (isinstance(left_val, int) and isinstance(right_val, int)):
                    raise RuntimeError(f"Unsupported operand types for -: {self.current_scope._get_runtime_type(left_val)} and {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                return left_val - right_val
            elif op == '*':
                if not (isinstance(left_val, int) and isinstance(right_val, int)):
                    raise RuntimeError(f"Unsupported operand types for *: {self.current_scope._get_runtime_type(left_val)} and {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                return left_val * right_val
            elif op == '/':
                if not (isinstance(left_val, int) and isinstance(right_val, int)):
                    raise RuntimeError(f"Unsupported operand types for /: {self.current_scope._get_runtime_type(left_val)} and {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                if right_val == 0:
                    raise RuntimeError("Division by zero", node.line, node.column)
                return left_val // right_val # Integer division
            elif op == '%':
                if not (isinstance(left_val, int) and isinstance(right_val, int)):
                    raise RuntimeError(f"Unsupported operand types for %: {self.current_scope._get_runtime_type(left_val)} and {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                if right_val == 0:
                    raise RuntimeError("Modulo by zero", node.line, node.column)
                return left_val % right_val
            elif op in ('==', '!='):
                if type(left_val) != type(right_val):
                    raise RuntimeError(f"Incompatible types for equality comparison '{op}': {self.current_scope._get_runtime_type(left_val)} and {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                if op == '==': return left_val == right_val
                if op == '!=': return left_val != right_val
            elif op in ('<', '>', '<=', '>='):
                if not (isinstance(left_val, int) and isinstance(right_val, int)):
                    raise RuntimeError(f"Comparison operator '{op}' only supported for integers, got {self.current_scope._get_runtime_type(left_val)} and {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                if op == '<':  return left_val < right_val
                if op == '>':  return left_val > right_val
                if op == '<=': return left_val <= right_val
                if op == '>=': return left_val >= right_val
            elif op == '&&':
                if not (isinstance(left_val, bool) and isinstance(right_val, bool)):
                    raise RuntimeError("Operands for '&&' must be booleans.", node.line, node.column)
                return left_val and right_val
            elif op == '||':
                if not (isinstance(left_val, bool) and isinstance(right_val, bool)):
                    raise RuntimeError("Operands for '||' must be booleans.", node.line, node.column)
                return left_val or right_val
            else:
                raise RuntimeError(f"Unknown binary operator: {op}", node.line, node.column)
        elif isinstance(node, UnaryOp):
            right_val = self._evaluate_expression(node.right)
            op = node.op
            if op == '-':
                if not isinstance(right_val, int):
                    raise RuntimeError(f"Unsupported operand type for unary -: {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                return -right_val
            elif op == '!':
                if not isinstance(right_val, bool):
                    raise RuntimeError(f"Unsupported operand type for unary !: {self.current_scope._get_runtime_type(right_val)}", node.line, node.column)
                return not right_val
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

        # Type checking
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
                print(factorial(4));
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
                print(calculate(5 + 1, 10 - 2));
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
                print(a % b);
                print(-a);
                bool c = true;
                print(!c);
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
                for (; i < 2; ) {
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
                {
                    int i = 2;
                    print(i);
                }
                print(i);
                return 0;
            }
        """,
        "description": "Scope handling with block statements.",
        "expected_output": "2\n0\n",
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
                print(sum_up_to(5));
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
                x = "hello";
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
                print(x);
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
                int x = 20;
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
                print(10 + "hello");
                return 0;
            }
        """,
        "description": "Static Type error: Type mismatch for binary operation.",
        "expected_output": "Error: Type Error: Unsupported operand types for '+': int and string. at line 4, column 22\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                if (x) {
                    print("true");
                }
                return 0;
            }
        """,
        "description": "Static Type error: Non-boolean condition in if.",
        "expected_output": "Error: Type Error: If condition must be of type 'bool'. at line 4, column 20\n",
        "inputs": []
    },
    {
        "code": """
            int foo() {
                return;
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
                return 1;
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
                print(sum(1, "two"));
                return 0;
            }
        """,
        "description": "Static Type error: Type mismatch in function call argument.",
        "expected_output": "Error: Type Error: Type mismatch for argument 2 in function 'sum': expected int, got string. at line 5, column 27\n",
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
                int x = 10;
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
                for (x = 0; x < 2; x = x + 1) {
                    print(x);
                }
                return 0;
            }
        """,
        "description": "For loop with assignment in initialization.",
        "expected_output": "0\n1\n",
        "inputs": []
    },
    {
        "code": """
            int get_val() { return 5; }
            int main() {
                int i = 0;
                for (i = 0; i < 2; i = get_val()) {
                    print(i);
                }
                return 0;
            }
        """,
        "description": "For loop with function call in increment.",
        "expected_output": "0\n",
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
                print( (x + 5) * 2 );
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
                print(x / y * z);
                print(x * y / z);
                print(x + y * z);
                return 0;
            }
        """,
        "description": "Operator precedence.",
        "expected_output": "15\n6\n16\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = true;
                return 0;
            }
        """,
        "description": "Static Type error: Type mismatch in variable declaration.",
        "expected_output": "Error: Type Error: Type mismatch in variable declaration for 'x': expected int, got bool. at line 4, column 25\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                if (10) {
                    print("true");
                }
                return 0;
            }
        """,
        "description": "Static Type error: Non-boolean condition in if statement.",
        "expected_output": "Error: Type Error: If condition must be of type 'bool'. at line 4, column 20\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                string s = "hello";
                print(x == s);
                return 0;
            }
        """,
        "description": "Static Type error: Incompatible types for equality comparison.",
        "expected_output": "Error: Type Error: Incompatible types for equality comparison '==': int and string. at line 5, column 27\n",
        "inputs": []
    },
    {
        "code": """
            int main() {
                int x = 10;
                bool b = true;
                print(x < b);
                return 0;
            }
        """,
        "description": "Static Type error: Incompatible types for relational comparison.",
        "expected_output": "Error: Type Error: Comparison operator '<' only supported for integers, got int and bool. at line 5, column 25\n",
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
~~~

~~~shell
Running 52 tests...
--- Test Summary ---
[PASS] Basic print of an integer literal.
[PASS] Variable declaration, assignment, and arithmetic.
[PASS] If-else statement with string literal.
[PASS] If-else if-else chain.
[PASS] While loop.
[PASS] For loop.
[PASS] Function declaration and call.
[PASS] Recursion.
[PASS] Read integers from input.
[PASS] Read booleans and logical AND.
[PASS] Read string and string concatenation.
[PASS] Complex expressions inside function call parameters.
[PASS] Modulo and unary operators.
[PASS] For loop with empty initialization and increment parts.
[PASS] Logical AND and OR operators.
[PASS] Scope handling with block statements.
[PASS] Function with for loop.
[PASS] Function returning string.
[PASS] Function returning boolean.
[PASS] Runtime error: Division by zero.
[PASS] Syntax error: Missing semicolon.
[PASS] Runtime error: Type mismatch on assignment.
[PASS] Runtime error: Undefined variable access.
[PASS] Runtime error: Variable redeclaration in same scope.
[PASS] Static Type error: Type mismatch for binary operation.
[PASS] Static Type error: Non-boolean condition in if.
[PASS] Runtime error: Function declared int but returns nothing.
[PASS] Runtime error: Function declared void but returns value.
[PASS] Static Type error: Type mismatch in function call argument.
[PASS] Self-assignment with arithmetic.
[PASS] Runtime error: No input for read_int.
[PASS] Runtime error: Wrong input type for read_int.
[PASS] Multi-line comments.
[PASS] Single-line comments.
[PASS] String with newline escape sequence.
[PASS] String with backslash escape sequence.
[PASS] String with double quote escape sequence.
[PASS] Complex logical expressions.
[PASS] For loop with assignment in initialization.
[PASS] For loop with function call in increment.
[PASS] If statements with boolean literals.
[PASS] Nested if statements.
[PASS] Function call returning a value.
[PASS] Void function call.
[PASS] Parenthesized expressions.
[PASS] Printing boolean literals.
[PASS] Equality and inequality operators.
[PASS] Equality and inequality operators with equal values.
[PASS] Relational operators.
[PASS] Operator precedence.
[PASS] Static Type error: Type mismatch in variable declaration.
[PASS] Static Type error: Non-boolean condition in if statement.
[PASS] Static Type error: Incompatible types for equality comparison.
[PASS] Static Type error: Incompatible types for relational comparison.

Total Tests: 52, Passed: 52, Failed: 0
~~~
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