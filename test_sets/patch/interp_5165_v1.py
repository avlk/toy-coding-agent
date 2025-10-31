import sys
import argparse

# --- Language Specification ---
LANGUAGE_SPECIFICATION = """
# C-like Language Specification

This document describes the syntax and features of the C-like language interpreted by this program.

## 1. Data Types

The language supports the following basic data types:
*   `int`: Integer numbers (e.g., `10`, `-5`, `0`).
*   `bool`: Boolean values (`true`, `false`).
*   `string`: Sequences of characters enclosed in double quotes (e.g., `"hello world"`).
*   `void`: Used as a return type for functions that do not return a value.

## 2. Variables

Variables must be declared with a type before use.
*   **Declaration**: `type identifier;`
    *   Example: `int x;`
    *   Example: `bool is_active;`
    *   Example: `string name;`
*   **Declaration with Initialization**: `type identifier = expression;`
    *   Example: `int x = 10;`
    *   Example: `bool is_active = true;`
    *   Example: `string name = "Alice";`
*   **Assignment**: `identifier = expression;`
    *   Example: `x = 10;`
    *   Example: `is_active = true;`
    *   Example: `name = "Alice";`

## 3. Operators

### 3.1 Arithmetic Operators
*   `+`: Addition (for `int` and `string` concatenation)
*   `-`: Subtraction (for `int`)
*   `*`: Multiplication (for `int`)
*   `/`: Division (for `int`)
*   `%`: Modulo (for `int`)

### 3.2 Comparison Operators
*   `==`: Equal to
*   `!=`: Not equal to
*   `<`: Less than
*   `<=`: Less than or equal to
*   `>`: Greater than
*   `>=`: Greater than or equal to
    *   These operators work for `int`, `bool`, and `string` types.

### 3.3 Logical Operators
*   `&&`: Logical AND
*   `||`: Logical OR
*   `!`: Logical NOT
    *   These operators work on `bool` types.

### 3.4 Assignment Operator
*   `=`: Assigns the value of the right-hand side expression to the left-hand side variable.

## 4. Control Structures

### 4.1 If-Else Statement
Executes a block of code conditionally.
```
if (condition) {
    // code to execute if condition is true
} else {
    // code to execute if condition is false (optional)
}
```
*   `condition` must evaluate to a `bool`.

### 4.2 While Loop
Repeats a block of code as long as a condition is true.
```
while (condition) {
    // code to repeat
}
```
*   `condition` must evaluate to a `bool`.

### 4.3 For Loop
A C-style for loop with initialization, condition, and update expressions.
```
for (initialization; condition; update) {
    // code to repeat
}
```
*   `initialization`: An optional statement executed once before the loop starts (e.g., `int i = 0;` or `i = 0;`).
*   `condition`: An optional expression evaluated before each iteration. If true, the loop continues. If false, the loop terminates. If omitted, it defaults to `true`.
*   `update`: An optional statement executed after each iteration (e.g., `i = i + 1;`).

### 4.4 Blocks
A bare block `{ ... }` can be used to create a new scope.
```
{
    int x; // x is local to this block
}
// x is not accessible here
```

## 5. Functions

Functions allow encapsulating reusable blocks of code.
```
func return_type function_name(type1 param1, type2 param2, ...) {
    // function body
    return expression; // Optional, if return_type is not void
}
```
*   `return_type`: The type of value the function returns (`int`, `bool`, `string`, `void`).
*   `function_name`: An identifier for the function.
*   `param1, param2, ...`: Parameters, each with a type and an identifier.
*   `return expression;`: Returns a value. Must match `return_type`. Functions with `void` return type should not have a `return` statement with an expression.

## 6. Input/Output

The language provides built-in functions for I/O:
*   `print(expression1, expression2, ...)`: Prints the values of the expressions to standard output, separated by spaces, followed by a newline.
*   `read_int()`: Reads an integer from standard input.
*   `read_bool()`: Reads a boolean (`true` or `false`) from standard input.
*   `read_str()`: Reads a string from standard input.

## 7. Comments

Comments are supported using `//` for single-line comments and `/* ... */` for multi-line comments.

## 8. Example Program

```
func int factorial(int n) {
    if (n == 0) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

func void main() {
    int num;
    print("Enter a number:");
    num = read_int();
    print("Factorial of", num, "is", factorial(num));
}
```
"""

# --- Lexer ---

class Token:
    def __init__(self, type, value, line=None, column=None):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, line={self.line}, col={self.column})"

class LexerError(Exception):
    def __init__(self, message, line=None, column=None):
        super().__init__(f"Lexer Error at line {line}, column {column}: {message}" if line is not None else f"Lexer Error: {message}")
        self.line = line
        self.column = column

class Lexer:
    KEYWORDS = {
        'func', 'if', 'else', 'while', 'for', 'return',
        'int', 'bool', 'string', 'void', 'true', 'false',
        'print', 'read_int', 'read_bool', 'read_str' # Added built-in functions as keywords for lexer
    }

    OPERATORS = {
        '+', '-', '*', '/', '%', '=', '==', '!=', '<', '<=', '>', '>=',
        '&&', '||', '!', ';', ',', '(', ')', '{', '}'
    }

    # Longer operators must come before shorter ones for correct matching
    MULTI_CHAR_OPERATORS = {
        '==', '!=', '<=', '>=', '&&', '||'
    }

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.current_char = self.text[self.pos] if self.text else None
        self.line = 1
        self.column = 1
        self.tokens = []

    def advance(self):
        self.pos += 1
        self.column += 1
        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
        else:
            self.current_char = None

    def peek(self, offset=1):
        peek_pos = self.pos + offset
        if peek_pos < len(self.text):
            return self.text[peek_pos]
        return None

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            if self.current_char == '\n':
                self.line += 1
                self.column = 0 # Reset column for new line, advance will make it 1
            self.advance()

    def skip_comment(self):
        if self.current_char == '/' and self.peek() == '/':
            while self.current_char is not None and self.current_char != '\n':
                self.advance()
        elif self.current_char == '/' and self.peek() == '*':
            self.advance() # Consume '/'
            self.advance() # Consume '*'
            while True:
                if self.current_char is None:
                    raise LexerError("Unterminated multi-line comment", self.line, self.column)
                if self.current_char == '*' and self.peek() == '/':
                    self.advance() # Consume '*'
                    self.advance() # Consume '/'
                    break
                if self.current_char == '\n':
                    self.line += 1
                    self.column = 0
                self.advance()

    def number(self):
        result = ''
        start_col = self.column
        while self.current_char is not None and self.current_char.isdigit():
            result += self.current_char
            self.advance()
        return Token('INT_LITERAL', int(result), self.line, start_col)

    def string(self):
        result = ''
        start_col = self.column
        self.advance() # Consume opening quote
        while self.current_char is not None and self.current_char != '"':
            if self.current_char == '\\': # Basic escape sequence support
                self.advance()
                if self.current_char == 'n':
                    result += '\n'
                elif self.current_char == 't':
                    result += '\t'
                elif self.current_char == '"':
                    result += '"'
                elif self.current_char == '\\':
                    result += '\\'
                else:
                    raise LexerError(f"Invalid escape sequence '\\{self.current_char}'", self.line, self.column)
            else:
                result += self.current_char
            self.advance()
        if self.current_char is None:
            raise LexerError("Unterminated string literal", self.line, start_col)
        self.advance() # Consume closing quote
        return Token('STRING_LITERAL', result, self.line, start_col)

    def identifier(self):
        result = ''
        start_col = self.column
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
        
        if result in {'true', 'false'}:
            return Token('BOOL_LITERAL', True if result == 'true' else False, self.line, start_col)
        elif result in self.KEYWORDS:
            return Token('KEYWORD', result, self.line, start_col)
        else:
            return Token('IDENTIFIER', result, self.line, start_col)

    def get_next_token(self):
        while True:
            self.skip_whitespace()
            
            # Check for comments after skipping whitespace
            if self.current_char == '/':
                if self.peek() == '/' or self.peek() == '*':
                    self.skip_comment()
                    continue # Go back to skip_whitespace and check for more comments/tokens
            
            if self.current_char is None:
                return Token('EOF', None, self.line, self.column)

            start_col = self.column

            if self.current_char.isalpha() or self.current_char == '_':
                return self.identifier()

            if self.current_char.isdigit():
                return self.number()

            if self.current_char == '"':
                return self.string()

            # Check for multi-character operators first
            for op in sorted(self.MULTI_CHAR_OPERATORS, key=len, reverse=True):
                if self.text[self.pos:self.pos + len(op)] == op:
                    for _ in range(len(op)):
                        self.advance()
                    return Token('OPERATOR', op, self.line, start_col)

            # Check for single-character operators
            if self.current_char in self.OPERATORS:
                op = self.current_char
                self.advance()
                return Token('OPERATOR', op, self.line, start_col)

            raise LexerError(f"Illegal character '{self.current_char}'", self.line, self.column)

    def tokenize(self):
        tokens = []
        while True:
            token = self.get_next_token()
            tokens.append(token)
            if token.type == 'EOF':
                break
        return tokens

# --- AST Nodes ---

class AST:
    pass

class Program(AST):
    def __init__(self, declarations):
        self.declarations = declarations # List of FunctionDecl

class FunctionDecl(AST):
    def __init__(self, return_type, name, params, body):
        self.return_type = return_type
        self.name = name
        self.params = params # List of ParamDecl
        self.body = body # Block

class ParamDecl(AST):
    def __init__(self, type, name):
        self.type = type
        self.name = name

class Block(AST):
    def __init__(self, statements):
        self.statements = statements # List of statements

class VarDecl(AST):
    def __init__(self, type, name, expression=None): # Added optional expression for initialization
        self.type = type
        self.name = name
        self.expression = expression

class IfStatement(AST):
    def __init__(self, condition, if_block, else_block=None):
        self.condition = condition
        self.if_block = if_block
        self.else_block = else_block

class WhileStatement(AST):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

class ForStatement(AST):
    def __init__(self, init, condition, update, body):
        self.init = init # Can be VarDecl or Assignment or FunctionCall
        self.condition = condition
        self.update = update # Can be Assignment or FunctionCall
        self.body = body

class ReturnStatement(AST):
    def __init__(self, expression=None):
        self.expression = expression

class Assignment(AST):
    def __init__(self, var_name, expression):
        self.var_name = var_name
        self.expression = expression

class FunctionCall(AST):
    def __init__(self, name, args):
        self.name = name
        self.args = args # List of expressions

class PrintStatement(AST):
    def __init__(self, args):
        self.args = args # List of expressions

class ReadIntCall(AST):
    pass

class ReadBoolCall(AST):
    pass

class ReadStrCall(AST):
    pass

class Identifier(AST):
    def __init__(self, name):
        self.name = name

class IntLiteral(AST):
    def __init__(self, value):
        self.value = value

class BoolLiteral(AST):
    def __init__(self, value):
        self.value = value

class StringLiteral(AST):
    def __init__(self, value):
        self.value = value

class BinaryOp(AST):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(AST):
    def __init__(self, op, right):
        self.op = op
        self.right = right

# --- Parser ---

class ParserError(Exception):
    def __init__(self, message, token=None):
        if token:
            super().__init__(f"Parser Error at line {token.line}, column {token.column}: {message} (Got '{token.value}' of type {token.type})")
        else:
            super().__init__(f"Parser Error: {message}")
        self.token = token

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.token_idx = 0
        self.current_token = self.tokens[self.token_idx]

    def advance(self):
        self.token_idx += 1
        if self.token_idx < len(self.tokens):
            self.current_token = self.tokens[self.token_idx]
        else:
            self.current_token = Token('EOF', None)

    def eat(self, token_type, value=None):
        if self.current_token.type == token_type and (value is None or self.current_token.value == value):
            token = self.current_token
            self.advance()
            return token
        else:
            expected = f"'{value}' ({token_type})" if value else token_type
            raise ParserError(f"Expected {expected}", self.current_token)

    def peek(self, offset=1):
        peek_idx = self.token_idx + offset
        if peek_idx < len(self.tokens):
            return self.tokens[peek_idx]
        return Token('EOF', None)

    # Grammar rules (recursive descent)

    def parse_program(self):
        declarations = []
        while self.current_token.type != 'EOF':
            declarations.append(self.parse_function_declaration())
        return Program(declarations)

    def parse_function_declaration(self):
        self.eat('KEYWORD', 'func')
        return_type_token = self.eat('KEYWORD')
        if return_type_token.value not in {'int', 'bool', 'string', 'void'}:
            raise ParserError(f"Expected a valid return type (int, bool, string, void), got '{return_type_token.value}'", return_type_token)
        return_type = return_type_token.value
        
        name = self.eat('IDENTIFIER').value
        self.eat('OPERATOR', '(')
        params = []
        if self.current_token.value != ')':
            params.append(self.parse_param_declaration())
            while self.current_token.value == ',':
                self.eat('OPERATOR', ',')
                params.append(self.parse_param_declaration())
        self.eat('OPERATOR', ')')
        body = self.parse_block()
        return FunctionDecl(return_type, name, params, body)

    def parse_param_declaration(self):
        param_type_token = self.eat('KEYWORD')
        if param_type_token.value not in {'int', 'bool', 'string'}:
            raise ParserError(f"Expected a valid parameter type (int, bool, string), got '{param_type_token.value}'", param_type_token)
        param_type = param_type_token.value
        param_name = self.eat('IDENTIFIER').value
        return ParamDecl(param_type, param_name)

    def parse_block(self):
        self.eat('OPERATOR', '{')
        statements = []
        while self.current_token.value != '}':
            statements.append(self.parse_statement())
        self.eat('OPERATOR', '}')
        return Block(statements)

    def parse_statement(self):
        if self.current_token.type == 'KEYWORD':
            if self.current_token.value in {'int', 'bool', 'string'}:
                return self.parse_variable_declaration()
            elif self.current_token.value == 'if':
                return self.parse_if_statement()
            elif self.current_token.value == 'while':
                return self.parse_while_statement()
            elif self.current_token.value == 'for':
                return self.parse_for_statement()
            elif self.current_token.value == 'return':
                return self.parse_return_statement()
            elif self.current_token.value == 'print':
                return self.parse_print_statement()
        elif self.current_token.type == 'IDENTIFIER':
            # Could be assignment or function call
            if self.peek().value == '=':
                return self.parse_assignment_statement()
            elif self.peek().value == '(':
                return self.parse_function_call_statement()
        elif self.current_token.value == '{': # Bare block statement
            return self.parse_block()
        
        raise ParserError(f"Unexpected token '{self.current_token.value}' for statement start", self.current_token)

    def parse_variable_declaration(self):
        var_type_token = self.eat('KEYWORD')
        if var_type_token.value not in {'int', 'bool', 'string'}:
            raise ParserError(f"Expected a valid type (int, bool, string), got '{var_type_token.value}'", var_type_token)
        var_type = var_type_token.value
        var_name = self.eat('IDENTIFIER').value
        expr = None
        if self.current_token.value == '=':
            self.eat('OPERATOR', '=')
            expr = self.parse_expression()
        self.eat('OPERATOR', ';')
        return VarDecl(var_type, var_name, expr)

    def parse_assignment_statement(self):
        var_name = self.eat('IDENTIFIER').value
        self.eat('OPERATOR', '=')
        expression = self.parse_expression()
        self.eat('OPERATOR', ';')
        return Assignment(var_name, expression)

    def parse_if_statement(self):
        self.eat('KEYWORD', 'if')
        self.eat('OPERATOR', '(')
        condition = self.parse_expression()
        self.eat('OPERATOR', ')')
        if_block = self.parse_block()
        else_block = None
        if self.current_token.value == 'else':
            self.eat('KEYWORD', 'else')
            else_block = self.parse_block()
        return IfStatement(condition, if_block, else_block)

    def parse_while_statement(self):
        self.eat('KEYWORD', 'while')
        self.eat('OPERATOR', '(')
        condition = self.parse_expression()
        self.eat('OPERATOR', ')')
        body = self.parse_block()
        return WhileStatement(condition, body)

    def parse_for_statement(self):
        self.eat('KEYWORD', 'for')
        self.eat('OPERATOR', '(')
        
        init = None
        if self.current_token.value != ';':
            if self.current_token.type == 'KEYWORD' and self.current_token.value in {'int', 'bool', 'string'}:
                init = self.parse_variable_declaration_no_semicolon() # VarDecl without trailing semicolon
            elif self.current_token.type == 'IDENTIFIER' and self.peek().value == '=':
                init = self.parse_assignment_no_semicolon() # Assignment without trailing semicolon
            elif self.current_token.type == 'IDENTIFIER' and self.peek().value == '(':
                init = self.parse_function_call_no_semicolon() # Function call in init
            else:
                raise ParserError("Invalid for loop initialization", self.current_token)
        self.eat('OPERATOR', ';')

        condition = None
        if self.current_token.value != ';':
            condition = self.parse_expression()
        self.eat('OPERATOR', ';')

        update = None
        if self.current_token.value != ')':
            if self.current_token.type == 'IDENTIFIER' and self.peek().value == '=':
                update = self.parse_assignment_no_semicolon()
            elif self.current_token.type == 'IDENTIFIER' and self.peek().value == '(':
                update = self.parse_function_call_no_semicolon()
            else:
                raise ParserError("Invalid for loop update expression", self.current_token)
        self.eat('OPERATOR', ')')
        
        body = self.parse_block()
        return ForStatement(init, condition, update, body)

    def parse_variable_declaration_no_semicolon(self):
        var_type_token = self.eat('KEYWORD')
        if var_type_token.value not in {'int', 'bool', 'string'}:
            raise ParserError(f"Expected a valid type (int, bool, string), got '{var_type_token.value}'", var_type_token)
        var_type = var_type_token.value
        var_name = self.eat('IDENTIFIER').value
        expr = None
        if self.current_token.value == '=':
            self.eat('OPERATOR', '=')
            expr = self.parse_expression()
        return VarDecl(var_type, var_name, expr)

    def parse_assignment_no_semicolon(self):
        var_name = self.eat('IDENTIFIER').value
        self.eat('OPERATOR', '=')
        expression = self.parse_expression()
        return Assignment(var_name, expression)

    def parse_function_call_no_semicolon(self):
        name_token = self.eat('IDENTIFIER')
        name = name_token.value
        self.eat('OPERATOR', '(')
        args = []
        if self.current_token.value != ')':
            args.append(self.parse_expression())
            while self.current_token.value == ',':
                self.eat('OPERATOR', ',')
                args.append(self.parse_expression())
        self.eat('OPERATOR', ')')
        return FunctionCall(name, args)

    def parse_return_statement(self):
        self.eat('KEYWORD', 'return')
        expr = None
        if self.current_token.value != ';':
            expr = self.parse_expression()
        self.eat('OPERATOR', ';')
        return ReturnStatement(expr)

    def parse_print_statement(self):
        self.eat('KEYWORD', 'print')
        self.eat('OPERATOR', '(')
        args = []
        if self.current_token.value != ')':
            args.append(self.parse_expression())
            while self.current_token.value == ',':
                self.eat('OPERATOR', ',')
                args.append(self.parse_expression())
        self.eat('OPERATOR', ')')
        self.eat('OPERATOR', ';')
        return PrintStatement(args)

    def parse_function_call_statement(self):
        call = self.parse_function_call_no_semicolon()
        self.eat('OPERATOR', ';')
        return call # FunctionCall is also a statement if its return value is ignored

    # Expression parsing (precedence climbing / shunting yard like)
    # Operators precedence (lowest to highest):
    # ||
    # &&
    # ==, !=, <, <=, >, >=
    # +, -
    # *, /, %
    # ! (unary)

    def parse_expression(self):
        return self.parse_logical_or_expression()

    def parse_logical_or_expression(self):
        node = self.parse_logical_and_expression()
        while self.current_token.value == '||':
            op_token = self.eat('OPERATOR', '||')
            node = BinaryOp(node, op_token.value, self.parse_logical_and_expression())
        return node

    def parse_logical_and_expression(self):
        node = self.parse_equality_expression()
        while self.current_token.value == '&&':
            op_token = self.eat('OPERATOR', '&&')
            node = BinaryOp(node, op_token.value, self.parse_equality_expression())
        return node

    def parse_equality_expression(self):
        node = self.parse_relational_expression()
        while self.current_token.value in ('==', '!='):
            op_token = self.eat('OPERATOR')
            node = BinaryOp(node, op_token.value, self.parse_relational_expression())
        return node

    def parse_relational_expression(self):
        node = self.parse_additive_expression()
        while self.current_token.value in ('<', '<=', '>', '>='):
            op_token = self.eat('OPERATOR')
            node = BinaryOp(node, op_token.value, self.parse_additive_expression())
        return node

    def parse_additive_expression(self):
        node = self.parse_multiplicative_expression()
        while self.current_token.value in ('+', '-'):
            op_token = self.eat('OPERATOR')
            node = BinaryOp(node, op_token.value, self.parse_multiplicative_expression())
        return node

    def parse_multiplicative_expression(self):
        node = self.parse_unary_expression()
        while self.current_token.value in ('*', '/', '%'):
            op_token = self.eat('OPERATOR')
            node = BinaryOp(node, op_token.value, self.parse_unary_expression())
        return node

    def parse_unary_expression(self):
        if self.current_token.value == '!':
            op_token = self.eat('OPERATOR', '!')
            return UnaryOp(op_token.value, self.parse_unary_expression())
        elif self.current_token.value == '-': # Unary minus
            op_token = self.eat('OPERATOR', '-')
            return UnaryOp(op_token.value, self.parse_unary_expression())
        return self.parse_primary_expression()

    def parse_primary_expression(self):
        token = self.current_token
        if token.type == 'INT_LITERAL':
            self.eat('INT_LITERAL')
            return IntLiteral(token.value)
        elif token.type == 'BOOL_LITERAL':
            self.eat('BOOL_LITERAL')
            return BoolLiteral(token.value)
        elif token.type == 'STRING_LITERAL':
            self.eat('STRING_LITERAL')
            return StringLiteral(token.value)
        elif token.type == 'IDENTIFIER':
            if self.peek().value == '(': # Function call
                return self.parse_function_call_no_semicolon()
            else: # Variable
                self.eat('IDENTIFIER')
                return Identifier(token.value)
        elif token.value == '(':
            self.eat('OPERATOR', '(')
            node = self.parse_expression()
            self.eat('OPERATOR', ')')
            return node
        elif token.type == 'KEYWORD' and token.value == 'read_int': # Corrected: check KEYWORD type
            self.eat('KEYWORD', 'read_int')
            self.eat('OPERATOR', '(')
            self.eat('OPERATOR', ')')
            return ReadIntCall()
        elif token.type == 'KEYWORD' and token.value == 'read_bool': # Corrected: check KEYWORD type
            self.eat('KEYWORD', 'read_bool')
            self.eat('OPERATOR', '(')
            self.eat('OPERATOR', ')')
            return ReadBoolCall()
        elif token.type == 'KEYWORD' and token.value == 'read_str': # Corrected: check KEYWORD type
            self.eat('KEYWORD', 'read_str')
            self.eat('OPERATOR', '(')
            self.eat('OPERATOR', ')')
            return ReadStrCall()
        else:
            raise ParserError(f"Unexpected token '{token.value}' in expression", token)

    def parse(self):
        return self.parse_program()

# --- Type Checker / Semantic Analyzer ---
# For simplicity, type checking will be integrated into the interpreter's execution phase.
# This means it's dynamic type checking, not static.
# A full static type checker would involve traversing the AST before execution
# and building a symbol table with types, then verifying all operations.
# Given the scope, dynamic checking during interpretation is more feasible.
# I will add a `Type` enum or similar to help with this.

class Type:
    INT = 'int'
    BOOL = 'bool'
    STRING = 'string'
    VOID = 'void'
    UNKNOWN = 'unknown'

class InterpreterError(Exception):
    def __init__(self, message, node=None):
        line = node.line if hasattr(node, 'line') else '?'
        column = node.column if hasattr(node, 'column') else '?'
        super().__init__(f"Runtime Error at line {line}, column {column}: {message}" if node else f"Runtime Error: {message}")
        self.node = node

class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value

class BreakLoop(Exception):
    pass

class ContinueLoop(Exception):
    pass

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def define(self, name, value, type):
        # print(f"DEBUG: Defining '{name}' as type '{type}' with value '{value}'") # Debug
        if name in self.symbols:
            raise InterpreterError(f"Variable '{name}' already declared in this scope.")
        self.symbols[name] = {'value': value, 'type': type}

    def assign(self, name, value, type=None):
        if name in self.symbols:
            if type is not None and self.symbols[name]['type'] != type:
                raise InterpreterError(f"Type mismatch: Cannot assign {type(value).__name__} to variable '{name}' of type {self.symbols[name]['type']}.")
            self.symbols[name]['value'] = value
            return
        elif self.parent:
            self.parent.assign(name, value, type)
            return
        raise InterpreterError(f"Undefined variable '{name}'.")

    def get(self, name):
        # print(f"DEBUG: Getting value for '{name}'. Current scope symbols: {self.symbols.keys()}") # Debug
        if name in self.symbols:
            return self.symbols[name]['value']
        elif self.parent:
            return self.parent.get(name)
        raise InterpreterError(f"Undefined variable '{name}'.")

    def get_type(self, name):
        # print(f"DEBUG: Getting type for '{name}'. Current scope symbols: {self.symbols.keys()}") # Debug
        if name in self.symbols:
            # print(f"DEBUG: Found '{name}' in current scope, type: {self.symbols[name]['type']}") # Debug
            return self.symbols[name]['type']
        elif self.parent:
            # print(f"DEBUG: '{name}' not in current scope, checking parent.") # Debug
            return self.parent.get_type(name)
        raise InterpreterError(f"Undefined variable '{name}'.")

    def has(self, name):
        return name in self.symbols or (self.parent and self.parent.has(name))

class Interpreter:
    def __init__(self, ast, input_queue=None):
        self.ast = ast
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.functions = {}
        self.output_buffer = []
        self.input_queue = input_queue if input_queue is not None else []
        self.input_idx = 0

        self._setup_builtins()

    def _setup_builtins(self):
        # Built-in functions are handled directly in visit_FunctionCall
        pass

    def get_input(self, expected_type):
        if self.input_idx >= len(self.input_queue):
            raise InterpreterError("Not enough input provided for read_* call.")
        
        value = self.input_queue[self.input_idx]
        self.input_idx += 1

        # Python's bool is a subclass of int, so check bool first
        if expected_type == Type.BOOL:
            if not isinstance(value, bool):
                raise InterpreterError(f"Expected boolean input, but got {type(value).__name__}.")
        elif expected_type == Type.INT:
            if not isinstance(value, int) or isinstance(value, bool): # Exclude bools from int
                raise InterpreterError(f"Expected integer input, but got {type(value).__name__}.")
        elif expected_type == Type.STRING:
            if not isinstance(value, str):
                raise InterpreterError(f"Expected string input, but got {type(value).__name__}.")
        
        return value

    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise InterpreterError(f'No visit_{type(node).__name__} method', node)

    def visit_Program(self, node):
        for decl in node.declarations:
            self.visit(decl) # Register functions

    def visit_FunctionDecl(self, node):
        if node.name in self.functions:
            raise InterpreterError(f"Function '{node.name}' already defined.")
        self.functions[node.name] = node
        # Functions are not executed here, just registered.

    def visit_Block(self, node):
        previous_scope = self.current_scope
        self.current_scope = SymbolTable(previous_scope)
        try:
            for statement in node.statements:
                self.visit(statement)
        finally:
            self.current_scope = previous_scope

    def visit_VarDecl(self, node):
        # Initialize variables to default values or provided expression
        if node.expression:
            initial_value = self.visit(node.expression)
            # Type check initial_value against node.type
            if node.type == Type.INT and (not isinstance(initial_value, int) or isinstance(initial_value, bool)):
                raise InterpreterError(f"Type mismatch: Cannot initialize int variable '{node.name}' with {type(initial_value).__name__}.", node.expression)
            elif node.type == Type.BOOL and not isinstance(initial_value, bool):
                raise InterpreterError(f"Type mismatch: Cannot initialize bool variable '{node.name}' with {type(initial_value).__name__}.", node.expression)
            elif node.type == Type.STRING and not isinstance(initial_value, str):
                raise InterpreterError(f"Type mismatch: Cannot initialize string variable '{node.name}' with {type(initial_value).__name__}.", node.expression)
            self.current_scope.define(node.name, initial_value, node.type)
        else:
            default_value = None
            if node.type == Type.INT:
                default_value = 0
            elif node.type == Type.BOOL:
                default_value = False
            elif node.type == Type.STRING:
                default_value = ""
            else:
                raise InterpreterError(f"Unsupported type for variable declaration: {node.type}")
            self.current_scope.define(node.name, default_value, node.type)

    def visit_Assignment(self, node):
        value = self.visit(node.expression)
        var_type = self.current_scope.get_type(node.var_name)
        
        # Type checking during assignment
        if var_type == Type.INT and (not isinstance(value, int) or isinstance(value, bool)):
            raise InterpreterError(f"Type mismatch: Cannot assign {type(value).__name__} to int variable '{node.var_name}'.", node)
        if var_type == Type.BOOL and not isinstance(value, bool):
            raise InterpreterError(f"Type mismatch: Cannot assign {type(value).__name__} to bool variable '{node.var_name}'.", node)
        if var_type == Type.STRING and not isinstance(value, str):
            raise InterpreterError(f"Type mismatch: Cannot assign {type(value).__name__} to string variable '{node.var_name}'.", node)

        self.current_scope.assign(node.var_name, value, var_type)

    def visit_IfStatement(self, node):
        condition_value = self.visit(node.condition)
        if not isinstance(condition_value, bool):
            raise InterpreterError(f"If condition must be a boolean, got {type(condition_value).__name__}.", node.condition)
        if condition_value:
            self.visit(node.if_block)
        elif node.else_block:
            self.visit(node.else_block)

    def visit_WhileStatement(self, node):
        while True:
            condition_value = self.visit(node.condition)
            if not isinstance(condition_value, bool):
                raise InterpreterError(f"While condition must be a boolean, got {type(condition_value).__name__}.", node.condition)
            if not condition_value:
                break
            try:
                self.visit(node.body)
            except BreakLoop:
                break
            except ContinueLoop:
                continue

    def visit_ForStatement(self, node):
        previous_scope = self.current_scope
        self.current_scope = SymbolTable(previous_scope) # For loop has its own scope for init
        try:
            if node.init:
                self.visit(node.init) # Execute initialization
            
            while True:
                condition_value = True # Default to true if condition is None
                if node.condition:
                    condition_value = self.visit(node.condition)
                    if not isinstance(condition_value, bool):
                        raise InterpreterError(f"For loop condition must be a boolean, got {type(condition_value).__name__}.", node.condition)
                
                if not condition_value:
                    break
                
                try:
                    self.visit(node.body)
                except BreakLoop:
                    break
                except ContinueLoop:
                    pass # Continue to update expression
                
                if node.update:
                    self.visit(node.update) # Execute update expression
        finally:
            self.current_scope = previous_scope

    def visit_ReturnStatement(self, node):
        if node.expression:
            value = self.visit(node.expression)
            raise ReturnValue(value)
        else:
            raise ReturnValue(None) # For void functions

    def visit_PrintStatement(self, node):
        values_to_print = []
        for arg in node.args:
            values_to_print.append(str(self.visit(arg)))
        self.output_buffer.append(" ".join(values_to_print))

    def visit_FunctionCall(self, node):
        # Built-in I/O functions are now handled by their specific AST nodes (ReadIntCall etc.)
        # This FunctionCall visit method is only for user-defined functions.
        
        if node.name not in self.functions:
            raise InterpreterError(f"Undefined function '{node.name}'.", node)
        
        func_decl = self.functions[node.name]
        if len(node.args) != len(func_decl.params):
            raise InterpreterError(f"Function '{node.name}' expected {len(func_decl.params)} arguments, but got {len(node.args)}.", node)

        # Evaluate arguments in current scope
        arg_values = [self.visit(arg_expr) for arg_expr in node.args]

        # Create new scope for function call
        previous_scope = self.current_scope
        self.current_scope = SymbolTable(self.global_scope) # Function scope is global-parented

        # Bind parameters
        for i, param_decl in enumerate(func_decl.params):
            param_name = param_decl.name
            param_type = param_decl.type
            arg_value = arg_values[i]

            # Type check arguments
            if param_type == Type.INT and (not isinstance(arg_value, int) or isinstance(arg_value, bool)):
                raise InterpreterError(f"Type mismatch for argument '{param_name}' in function '{node.name}': Expected int, got {type(arg_value).__name__}.", node.args[i])
            if param_type == Type.BOOL and not isinstance(arg_value, bool):
                raise InterpreterError(f"Type mismatch for argument '{param_name}' in function '{node.name}': Expected bool, got {type(arg_value).__name__}.", node.args[i])
            if param_type == Type.STRING and not isinstance(arg_value, str):
                raise InterpreterError(f"Type mismatch for argument '{param_name}' in function '{node.name}': Expected string, got {type(arg_value).__name__}.", node.args[i])
            
            self.current_scope.define(param_name, arg_value, param_type)

        return_value = None
        try:
            self.visit(func_decl.body)
        except ReturnValue as e:
            return_value = e.value
        finally:
            self.current_scope = previous_scope # Restore previous scope

        # Check return type
        if func_decl.return_type == Type.VOID:
            if return_value is not None:
                raise InterpreterError(f"Function '{node.name}' declared void but returned a value.", node)
            return None
        else:
            if return_value is None:
                raise InterpreterError(f"Function '{node.name}' declared to return {func_decl.return_type} but returned nothing.", node)
            
            # Type check the returned value
            if func_decl.return_type == Type.INT and (not isinstance(return_value, int) or isinstance(return_value, bool)):
                raise InterpreterError(f"Type mismatch: Function '{node.name}' expected to return int, got {type(return_value).__name__}.", node)
            if func_decl.return_type == Type.BOOL and not isinstance(return_value, bool):
                raise InterpreterError(f"Type mismatch: Function '{node.name}' expected to return bool, got {type(return_value).__name__}.", node)
            if func_decl.return_type == Type.STRING and not isinstance(return_value, str):
                raise InterpreterError(f"Type mismatch: Function '{node.name}' expected to return string, got {type(return_value).__name__}.", node)
            
            return return_value

    def visit_ReadIntCall(self, node):
        return self.get_input(Type.INT)

    def visit_ReadBoolCall(self, node):
        return self.get_input(Type.BOOL)

    def visit_ReadStrCall(self, node):
        return self.get_input(Type.STRING)

    def visit_Identifier(self, node):
        return self.current_scope.get(node.name)

    def visit_IntLiteral(self, node):
        return node.value

    def visit_BoolLiteral(self, node):
        return node.value

    def visit_StringLiteral(self, node):
        return node.value

    def visit_BinaryOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op

        # Type checking and operation
        if op == '+':
            if isinstance(left, int) and isinstance(right, int):
                return left + right
            elif isinstance(left, str) and isinstance(right, str):
                return left + right
            else:
                raise InterpreterError(f"Unsupported operand types for '+': {type(left).__name__} and {type(right).__name__}.", node)
        elif op == '-':
            if isinstance(left, int) and isinstance(right, int):
                return left - right
            else:
                raise InterpreterError(f"Unsupported operand types for '-': {type(left).__name__} and {type(right).__name__}.", node)
        elif op == '*':
            if isinstance(left, int) and isinstance(right, int):
                return left * right
            else:
                raise InterpreterError(f"Unsupported operand types for '*': {type(left).__name__} and {type(right).__name__}.", node)
        elif op == '/':
            if isinstance(left, int) and isinstance(right, int):
                if right == 0:
                    raise InterpreterError("Division by zero.", node)
                return left // right # Integer division
            else:
                raise InterpreterError(f"Unsupported operand types for '/': {type(left).__name__} and {type(right).__name__}.", node)
        elif op == '%':
            if isinstance(left, int) and isinstance(right, int):
                if right == 0:
                    raise InterpreterError("Modulo by zero.", node)
                return left % right
            else:
                raise InterpreterError(f"Unsupported operand types for '%': {type(left).__name__} and {type(right).__name__}.", node)
        elif op == '&&':
            if isinstance(left, bool) and isinstance(right, bool):
                return left and right
            else:
                raise InterpreterError(f"Unsupported operand types for '&&': {type(left).__name__} and {type(right).__name__}.", node)
        elif op == '||':
            if isinstance(left, bool) and isinstance(right, bool):
                return left or right
            else:
                raise InterpreterError(f"Unsupported operand types for '||': {type(left).__name__} and {type(right).__name__}.", node)
        elif op in ('==', '!=', '<', '<=', '>', '>='):
            # All comparison operators
            if type(left) != type(right):
                raise InterpreterError(f"Cannot compare different types: {type(left).__name__} and {type(right).__name__}.", node)
            
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '<':  return left < right
            if op == '<=': return left <= right
            if op == '>':  return left > right
            if op == '>=': return left >= right
        
        raise InterpreterError(f"Unknown binary operator '{op}'.", node)

    def visit_UnaryOp(self, node):
        right = self.visit(node.right)
        op = node.op

        if op == '!':
            if isinstance(right, bool):
                return not right
            else:
                raise InterpreterError(f"Unsupported operand type for '!': {type(right).__name__}.", node)
        elif op == '-':
            if isinstance(right, int):
                return -right
            else:
                raise InterpreterError(f"Unsupported operand type for unary '-': {type(right).__name__}.", node)
        
        raise InterpreterError(f"Unknown unary operator '{op}'.", node)

    def interpret(self):
        # First pass: register all functions
        for decl in self.ast.declarations:
            if isinstance(decl, FunctionDecl):
                self.visit(decl)
            else:
                raise InterpreterError("Only function declarations are allowed at the global scope.", decl)
        
        # Find and execute the 'main' function
        if 'main' not in self.functions:
            raise InterpreterError("No 'main' function found.")
        
        main_func = self.functions['main']
        if main_func.params:
            raise InterpreterError("The 'main' function should not take any arguments.")
        if main_func.return_type != Type.VOID:
            raise InterpreterError("The 'main' function should have a 'void' return type.")
        
        try:
            self.visit(main_func.body)
        except ReturnValue as e:
            if e.value is not None:
                raise InterpreterError("main() function returned a value, but it should be void.")
        
        return "\n".join(self.output_buffer)

# --- Main Interpreter Entry Point ---

def interpreter_main(program_code: str, inputs: list = None) -> str:
    """
    Main entry point for the C-like language interpreter.
    
    Args:
        program_code (str): The multi-line text of the program.
        inputs (list, optional): A list of values to mock stdin for read_* calls.
                                 Defaults to None, meaning real stdin will be used.
                                 For testing, this list provides the inputs.
    
    Returns:
        str: The accumulated output of the program.
    
    Raises:
        LexerError: If a lexical error occurs.
        ParserError: If a syntax error occurs.
        InterpreterError: If a runtime error occurs.
    """
    try:
        lexer = Lexer(program_code)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        interpreter = Interpreter(ast, inputs)
        output = interpreter.interpret()
        
        return output
    except (LexerError, ParserError, InterpreterError) as e:
        # Re-raise the error to be caught by the test runner or main CLI
        raise e
    except Exception as e:
        # Catch any unexpected errors
        # This generic catch-all might be masking specific issues.
        # For debugging, it's better to let specific exceptions propagate.
        # For final submission, a general catch is okay if it provides useful info.
        raise InterpreterError(f"An unexpected error occurred: {type(e).__name__}: {e}")

# --- Test Suite ---

TEST_PROGRAMS = [
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x);
}
""",
        "description": "Basic variable declaration and assignment, print integer.",
        "expected_output": "10",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int a;
    int b;
    a = 5;
    b = 3;
    print(a + b, a - b, a * b, a / b, a % b);
}
""",
        "description": "Basic arithmetic operations.",
        "expected_output": "8 2 15 1 2",
        "inputs": []
    },
    {
        "code": """
func void main() {
    bool t;
    bool f;
    t = true;
    f = false;
    print(t && f, t || f, !t, !f);
}
""",
        "description": "Boolean operations.",
        "expected_output": "False True False True",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    if (x > 5) {
        print("x is greater than 5");
    } else {
        print("x is not greater than 5");
    }
    x = 3;
    if (x > 5) {
        print("x is greater than 5");
    } else {
        print("x is not greater than 5");
    }
}
""",
        "description": "If-else statement.",
        "expected_output": "x is greater than 5\nx is not greater than 5",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int i;
    i = 0;
    while (i < 3) {
        print("Loop", i);
        i = i + 1;
    }
}
""",
        "description": "While loop.",
        "expected_output": "Loop 0\nLoop 1\nLoop 2",
        "inputs": []
    },
    {
        "code": """
func int add(int a, int b) {
    return a + b;
}

func void main() {
    int result;
    result = add(7, 3);
    print("Sum:", result);
}
""",
        "description": "Function definition and call with arguments and return value.",
        "expected_output": "Sum: 10",
        "inputs": []
    },
    {
        "code": """
func int factorial(int n) {
    if (n == 0) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}

func void main() {
    print("Factorial of 5 is", factorial(5));
    print("Factorial of 0 is", factorial(0));
}
""",
        "description": "Recursive function call (factorial).",
        "expected_output": "Factorial of 5 is 120\nFactorial of 0 is 1",
        "inputs": []
    },
    {
        "code": """
func void greet(string name) {
    print("Hello,", name, "!");
}

func void main() {
    string user_name;
    user_name = "World";
    greet(user_name);
    greet("Alice");
}
""",
        "description": "String type, string concatenation with print, function with string argument.",
        "expected_output": "Hello, World !\nHello, Alice !",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int num;
    print("Enter an integer:");
    num = read_int();
    print("You entered:", num);
    
    bool flag;
    print("Enter a boolean (true/false):");
    flag = read_bool();
    print("Flag is:", flag);

    string text;
    print("Enter a string:");
    text = read_str();
    print("Text is:", text);
}
""",
        "description": "I/O operations: read_int, read_bool, read_str.",
        "expected_output": "Enter an integer:\nYou entered: 123\nEnter a boolean (true/false):\nFlag is: True\nEnter a string:\nText is: test input",
        "inputs": [123, True, "test input"]
    },
    {
        "code": """
func int sum_up_to(int n) {
    int total;
    total = 0;
    for (int i = 1; i <= n; i = i + 1) { // This line now uses VarDecl with init
        total = total + i;
    }
    return total;
}

func void main() {
    print("Sum up to 5 is", sum_up_to(5));
    print("Sum up to 0 is", sum_up_to(0));
}
""",
        "description": "For loop with variable declaration and initialization in init, and function call.",
        "expected_output": "Sum up to 5 is 15\nSum up to 0 is 0",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int y;
    y = 20;
    if (x < y && x != y) {
        print("x is less than y and not equal");
    }
    if (x > y || x == y) {
        print("This should not print");
    } else {
        print("This should print");
    }
}
""",
        "description": "Complex boolean expressions in if conditions.",
        "expected_output": "x is less than y and not equal\nThis should print",
        "inputs": []
    },
    {
        "code": """
func int calculate(int a, int b, int c) {
    return (a + b) * c - (a / b);
}

func void main() {
    print("Result:", calculate(10, 2, 3)); // (10+2)*3 - (10/2) = 12*3 - 5 = 36 - 5 = 31
}
""",
        "description": "Complex arithmetic expressions inside function call parameters.",
        "expected_output": "Result: 31",
        "inputs": []
    },
    {
        "code": """
func void main() {
    string s1;
    string s2;
    s1 = "Hello";
    s2 = "World";
    print(s1 + " " + s2 + "!");
    print("Number: " + 123); // Type error: string + int
}
""",
        "description": "String concatenation and expected type error.",
        "expected_output": "Hello World !",
        "error_expected": True,
        "error_message_contains": "Unsupported operand types for '+': str and int"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int y;
    y = 0;
    print(x / y); // Division by zero
}
""",
        "description": "Runtime error: Division by zero.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Division by zero"
    },
    {
        "code": """
func int my_func(int a, bool b) {
    return a;
}
func void main() {
    int x;
    x = my_func(10, 20); // Type error: bool expected, got int
}
""",
        "description": "Runtime error: Function argument type mismatch.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Type mismatch for argument 'b' in function 'my_func': Expected bool, got int"
    },
    {
        "code": """
func int get_val() {
    return 10;
}
func void main() {
    int x;
    x = get_val();
    print(x);
    x = get_val(1); // Too many arguments
}
""",
        "description": "Runtime error: Function call with wrong number of arguments.",
        "expected_output": "10",
        "error_expected": True,
        "error_message_contains": "Function 'get_val' expected 0 arguments, but got 1"
    },
    {
        "code": """
func int get_val() {
    return true; // Return type mismatch
}
func void main() {
    int x;
    x = get_val();
    print(x);
}
""",
        "description": "Runtime error: Function return type mismatch.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Function 'get_val' expected to return int, got bool"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    x = "hello"; // Type mismatch assignment
}
""",
        "description": "Runtime error: Assignment type mismatch.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Type mismatch: Cannot assign str to int variable 'x'"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    if (x) { // Condition must be boolean
        print("This should not run");
    }
}
""",
        "description": "Runtime error: If condition not boolean.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "If condition must be a boolean, got int"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(y); // Undefined variable
}
""",
        "description": "Runtime error: Undefined variable.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Undefined variable 'y'"
    },
    {
        "code": """
func void main() {
    int x = 5; // Now valid syntax
    print(x);
}
""",
        "description": "Variable declaration with initialization.",
        "expected_output": "5",
        "error_expected": False, # Changed from True
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x);
}
""",
        "description": "Syntax error: Missing semicolon.",
        "expected_output": "", # Changed from "10"
        "error_expected": True,
        "error_message_contains": "Expected ';'"
    },
    {
        "code": """
func int get_five() {
    return 5;
}
func void main() {
    int x;
    for (x = 0; x < get_five(); x = x + 1) {
        print(x);
    }
}
""",
        "description": "For loop with function call in condition.",
        "expected_output": "0\n1\n2\n3\n4",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int i;
    for (i = 0; i < 5; i = i + 1) {
        if (i == 2) {
            continue_statement_placeholder;
        }
        print(i);
    }
}
""",
        "description": "Test for unsupported 'continue' (will cause error).",
        "expected_output": "0\n1\n2\n3\n4", # Expected output if continue was implemented
        "error_expected": True,
        "error_message_contains": "Unexpected token 'continue_statement_placeholder' for statement start"
    },
    {
        "code": """
func void main() {
    int i;
    for (i = 0; i < 5; i = i + 1) {
        if (i == 2) {
            break_statement_placeholder;
        }
        print(i);
    }
}
""",
        "description": "Test for unsupported 'break' (will cause error).",
        "expected_output": "0\n1", # Expected output if break was implemented
        "error_expected": True,
        "error_message_contains": "Unexpected token 'break_statement_placeholder' for statement start"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    { // Nested block scope
        int y;
        y = 20;
        print(x, y);
    }
    print(y); // y should be out of scope here, will cause error
}
""",
        "description": "Block scoping for variables (y should be undefined outside block).",
        "expected_output": "10 20",
        "error_expected": True,
        "error_message_contains": "Undefined variable 'y'"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    if (true) {
        int x; // Redeclaration in inner scope is fine
        x = 20;
        print(x);
    }
    print(x); // Outer x should be 10
}
""",
        "description": "Shadowing variables in inner scopes.",
        "expected_output": "20\n10",
        "inputs": []
    },
    {
        "code": """
func void main() {
    string s;
    s = "hello\\nworld";
    print(s);
    s = "tab\\tseparated";
    print(s);
    s = "quote\\\"inside";
    print(s);
    s = "backslash\\\\";
    print(s);
}
""",
        "description": "String escape sequences.",
        "expected_output": "hello\nworld\ntab\tseparated\nquote\"inside\nbackslash\\",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int a;
    a = 10;
    int b;
    b = 20;
    print(a == 10, a != 20, a < b, a <= 10, b > a, b >= 20);
    print("hello" == "hello", "hello" != "world", "apple" < "banana");
}
""",
        "description": "Comparison operators for int and string.",
        "expected_output": "True True True True True True\nTrue True True",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    for (; x > 5; x = x - 1) { // For loop with omitted init, x = x - 1
        print(x);
    }
}
""",
        "description": "For loop with omitted initialization.",
        "expected_output": "10\n9\n8\n7\n6",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    for (x = 0; ; x = x + 1) { // For loop with omitted condition (infinite loop)
        if (x == 3) {
            break_statement_placeholder;
        }
        print(x);
    }
}
""",
        "description": "For loop with omitted condition (expected infinite loop, but will hit error for break).",
        "expected_output": "0\n1\n2",
        "error_expected": True,
        "error_message_contains": "Unexpected token 'break_statement_placeholder' for statement start"
    },
    {
        "code": """
func void main() {
    int x;
    for (x = 0; x < 3; ) { // For loop with omitted update
        print(x);
        x = x + 1;
    }
}
""",
        "description": "For loop with omitted update.",
        "expected_output": "0\n1\n2",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = -5;
    print(-x);
    bool b;
    b = true;
    print(!b);
}
""",
        "description": "Unary operators: negation and logical NOT.",
        "expected_output": "5\nFalse",
        "inputs": []
    },
    {
        "code": """
func int get_int() { return 10; }
func bool get_bool() { return true; }
func string get_str() { return "hello"; }

func void main() {
    int x;
    x = get_int();
    print(x);
    bool b;
    b = get_bool();
    print(b);
    string s;
    s = get_str();
    print(s);
}
""",
        "description": "Functions returning different basic types.",
        "expected_output": "10\nTrue\nhello",
        "inputs": []
    },
    {
        "code": """
func void print_nothing() {
    // This function returns nothing
}

func void main() {
    print_nothing();
    // int x = print_nothing(); // This should be a type error if print_nothing is void
}
""",
        "description": "Void function call (statement).",
        "expected_output": "",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int y;
    y = 20;
    if (x < y) {
        if (y > x) {
            print("Nested if works");
        }
    } else {
        print("This should not print");
    }
}
""",
        "description": "Nested if statements.",
        "expected_output": "Nested if works",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int i;
    i = 0;
    while (i < 5) {
        int j;
        j = 0;
        while (j < 2) {
            print("i:", i, "j:", j);
            j = j + 1;
        }
        i = i + 1;
    }
}
""",
        "description": "Nested while loops.",
        "expected_output": "i: 0 j: 0\ni: 0 j: 1\ni: 1 j: 0\ni: 1 j: 1\ni: 2 j: 0\ni: 2 j: 1\ni: 3 j: 0\ni: 3 j: 1\ni: 4 j: 0\ni: 4 j: 1",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    if (x == 10) {
        print("Equal");
    } else {
        if (x == 20) {
            print("Not equal");
        } else {
            print("Neither");
        }
    }
}
""",
        "description": "Simulated else-if (nested if-else).",
        "expected_output": "Equal",
        "inputs": []
    },
    {
        "code": """
func int calculate(int a, int b, int c) {
    return (a + b) * c - (a / b);
}

func void main() {
    print("Result:", calculate(10, 2, 3)); // (10+2)*3 - (10/2) = 12*3 - 5 = 36 - 5 = 31
}
""",
        "description": "Complex arithmetic expressions inside function call parameters.",
        "expected_output": "Result: 31",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int a;
    a = 1;
    int b;
    b = 2;
    int c;
    c = 3;
    print(a + b * c); // 1 + (2*3) = 7
    print((a + b) * c); // (1+2)*3 = 9
}
""",
        "description": "Operator precedence.",
        "expected_output": "7\n9",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int y;
    y = 20;
    int z;
    z = 30;
    print(x < y && y < z); // true && true -> true
    print(x > y || y < z); // false || true -> true
    print(!(x == y)); // !(false) -> true
}
""",
        "description": "Combined logical and comparison operators.",
        "expected_output": "True\nTrue\nTrue",
        "inputs": []
    },
    {
        "code": """
func void my_func(int x) {
    print("Inside func, x is", x);
    x = x + 1; // This changes local x, not global/caller's x
}

func void main() {
    int x;
    x = 5;
    print("Before func, x is", x);
    my_func(x);
    print("After func, x is", x); // Should still be 5 due to pass-by-value
}
""",
        "description": "Pass-by-value semantics for function arguments.",
        "expected_output": "Before func, x is 5\nInside func, x is 5\nAfter func, x is 5",
        "inputs": []
    },
    {
        "code": """
func void main() {
    // This is an invalid program, missing main function
}
""",
        "description": "Error: Missing main function.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "No 'main' function found."
    },
    {
        "code": """
func void main(int arg) { // main with arguments
    print(arg);
}
""",
        "description": "Error: main function with arguments.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "The 'main' function should not take any arguments."
    },
    {
        "code": """
func int main() { // main with non-void return type
    return 0;
}
""",
        "description": "Error: main function with non-void return type.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "The 'main' function should have a 'void' return type."
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int x; // Redeclaration in same scope
}
""",
        "description": "Error: Variable redeclaration in same scope.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Variable 'x' already declared in this scope."
    },
    {
        "code": """
func void test() {
    return 10; // Void function returning value
}
func void main() {
    test();
}
""",
        "description": "Error: Void function returning a value.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Function 'test' declared void but returned a value."
    },
    {
        "code": """
func int test() {
    // Non-void function not returning a value
}
func void main() {
    test();
}
""",
        "description": "Error: Non-void function not returning a value.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Function 'test' declared to return int but returned nothing."
    },
    {
        "code": """
func void main() {
    int x;
    x = read_int();
    print(x);
}
""",
        "description": "I/O: read_int with insufficient input.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Not enough input provided for read_* call."
    },
    {
        "code": """
func void main() {
    int x;
    x = read_int();
    print(x);
}
""",
        "description": "I/O: read_int with wrong type input.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Expected integer input, but got str.",
        "inputs": ["not an int"]
    },
    {
        "code": """
func void main() {
    bool b;
    b = read_bool();
    print(b);
}
""",
        "description": "I/O: read_bool with wrong type input.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Expected boolean input, but got int.",
        "inputs": [123]
    },
    {
        "code": """
func void main() {
    string s;
    s = read_str();
    print(s);
}
""",
        "description": "I/O: read_str with wrong type input.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Expected string input, but got bool.",
        "inputs": [True]
    },
    {
        "code": """
func void main() {
    print(read_int(1)); // read_int with arguments
}
""",
        "description": "Error: read_int with arguments.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "read_int() takes no arguments."
    },
    {
        "code": """
func void main() {
    int x;
    for (int i = 0; i < 3; i = i + 1) {
        x = i;
    }
    print(x);
}
""",
        "description": "For loop variable scope (x should be accessible outside loop if declared outside).",
        "expected_output": "2",
        "inputs": []
    },
    {
        "code": """
func void main() {
    for (int i = 0; i < 3; i = i + 1) {
        print(i);
    }
    print(i); // i should be out of scope here
}
""",
        "description": "For loop variable scope (i should be undefined outside loop).",
        "expected_output": "0\n1\n2",
        "error_expected": True,
        "error_message_contains": "Undefined variable 'i'"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x + "hello"); // Type mismatch: int + string
}
""",
        "description": "Type mismatch: int + string.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Unsupported operand types for '+': int and str"
    },
    {
        "code": """
func void main() {
    string s;
    s = "hello";
    print(s - "world"); // Type mismatch: string - string
}
""",
        "description": "Type mismatch: string - string.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Unsupported operand types for '-': str and str"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x == true); // Type mismatch: int == bool
}
""",
        "description": "Type mismatch: int == bool.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Cannot compare different types: int and bool"
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x == 10 && "hello"); // Type mismatch: bool && string
}
""",
        "description": "Type mismatch: bool && string.",
        "expected_output": "",
        "error_expected": True,
        "error_message_contains": "Unsupported operand types for '&&': bool and str"
    },
    {
        "code": """
func void main() {
    print(10 + (2 * 3)); // Parentheses for precedence
}
""",
        "description": "Parentheses for expression grouping.",
        "expected_output": "16",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int y;
    y = 20;
    int z;
    z = 30;
    print(x + y * z); // 10 + (20 * 30) = 610
}
""",
        "description": "Operator precedence (multiplication before addition).",
        "expected_output": "610",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int y;
    y = 20;
    int z;
    z = 30;
    print(x < y && y < z || x == z); // (true && true) || false -> true || false -> true
}
""",
        "description": "Complex logical expression with precedence.",
        "expected_output": "True",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x + 5 * 2 - 1); // 10 + 10 - 1 = 19
}
""",
        "description": "Mixed arithmetic operations.",
        "expected_output": "19",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    int y;
    y = 20;
    if (x < y) {
        print("x is less than y");
    }
    if (x > y) {
        print("x is greater than y");
    } else {
        print("x is not greater than y");
    }
}
""",
        "description": "Multiple if statements, one with else.",
        "expected_output": "x is less than y\nx is not greater than y",
        "inputs": []
    },
    {
        "code": """
func int get_val(int a) {
    return a + 1;
}
func void main() {
    int x;
    for (x = 0; x < 3; x = get_val(x)) { // For loop with function call in update
        print(x);
    }
}
""",
        "description": "For loop with function call in update.",
        "expected_output": "0\n1\n2",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x);
    x = 20; // Reassignment
    print(x);
}
""",
        "description": "Variable reassignment.",
        "expected_output": "10\n20",
        "inputs": []
    },
    {
        "code": """
func void main() {
    print("Hello", "World");
    print(1, 2, 3);
    print(true, false);
}
""",
        "description": "Print multiple arguments of different types.",
        "expected_output": "Hello World\n1 2 3\nTrue False",
        "inputs": []
    },
    {
        "code": """
func int fib(int n) {
    if (n <= 1) {
        return n;
    } else {
        return fib(n - 1) + fib(n - 2);
    }
}

func void main() {
    print("Fib(0) =", fib(0));
    print("Fib(1) =", fib(1));
    print("Fib(5) =", fib(5)); // 0 1 1 2 3 5
}
""",
        "description": "Recursive Fibonacci sequence.",
        "expected_output": "Fib(0) = 0\nFib(1) = 1\nFib(5) = 5",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    if (x == 10) {
        print("Condition is true");
    }
    // No else block
}
""",
        "description": "If statement without else block.",
        "expected_output": "Condition is true",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    if (x != 10) {
        print("Condition is false");
    } else {
        print("Condition is true");
    }
}
""",
        "description": "If-else where if condition is false.",
        "expected_output": "Condition is true",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int i;
    for (i = 0; i < 0; i = i + 1) {
        print("This should not print");
    }
    print("Loop finished");
}
""",
        "description": "For loop that doesn't execute.",
        "expected_output": "Loop finished",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int i;
    i = 0;
    while (i < 0) {
        print("This should not print");
    }
    print("Loop finished");
}
""",
        "description": "While loop that doesn't execute.",
        "expected_output": "Loop finished",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x + 5);
    print(x - 2);
    print(x * 3);
    print(x / 4);
    print(x % 3);
}
""",
        "description": "All arithmetic operators with literals.",
        "expected_output": "15\n8\n30\n2\n1",
        "inputs": []
    },
    {
        "code": """
func void main() {
    string s;
    s = "hello";
    print(s == "hello");
    print(s != "world");
    print(s < "world");
    print(s <= "hello");
    print(s > "apple");
    print(s >= "hello");
}
""",
        "description": "All comparison operators with string literals.",
        "expected_output": "True\nTrue\nTrue\nTrue\nTrue\nTrue",
        "inputs": []
    },
    {
        "code": """
func void main() {
    bool a;
    a = true;
    bool b;
    b = false;
    print(a && b);
    print(a || b);
    print(!a);
}
""",
        "description": "All logical operators with boolean variables.",
        "expected_output": "False\nTrue\nFalse",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 1;
    { // Bare block
        int x; // Shadowing
        x = 2;
        { // Another bare block
            int x; // Further shadowing
            x = 3;
            print(x); // 3
        }
        print(x); // 2
    }
    print(x); // 1
}
""",
        "description": "Deeply nested scopes and shadowing.",
        "expected_output": "3\n2\n1",
        "inputs": []
    },
    {
        "code": """
func int get_val() {
    return 10;
}
func void main() {
    int x;
    x = get_val();
    print(x);
    x = get_val() + 5;
    print(x);
}
""",
        "description": "Function call as part of an expression.",
        "expected_output": "10\n15",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x + (5 * (2 + 1))); // 10 + (5 * 3) = 10 + 15 = 25
}
""",
        "description": "Complex nested expressions with parentheses.",
        "expected_output": "25",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    print(x == 10 && (true || false)); // true && true -> true
}
""",
        "description": "Complex logical expression with nested parentheses.",
        "expected_output": "True",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 10;
    if (x == 10) {
        print("A");
    } else {
        if (x == 20) {
            print("B");
        } else {
            print("C");
        }
    }
}
""",
        "description": "Nested if-else for else-if simulation.",
        "expected_output": "A",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 20;
    if (x == 10) {
        print("A");
    } else {
        if (x == 20) {
            print("B");
        } else {
            print("C");
        }
    }
}
""",
        "description": "Nested if-else for else-if simulation (middle condition).",
        "expected_output": "B",
        "inputs": []
    },
    {
        "code": """
func void main() {
    int x;
    x = 30;
    if (x == 10) {
        print("A");
    } else {
        if (x == 20) {
            print("B");
        } else {
            print("C");
        }
    }
}
""",
        "description": "Nested if-else for else-if simulation (last condition).",
        "expected_output": "C",
        "inputs": []
    },
]

# --- Command Line Interface and Test Runner ---

def run_tests():
    print("Running embedded tests...")
    total_tests = len(TEST_PROGRAMS)
    passed_tests = 0
    
    for i, test_case in enumerate(TEST_PROGRAMS):
        print(f"\n--- Test {i+1}/{total_tests}: {test_case['description']} ---")
        actual_output = ""
        error_occurred = False
        error_message = ""

        try:
            actual_output = interpreter_main(test_case["code"], test_case["inputs"])
            if "error_expected" in test_case and test_case["error_expected"]:
                error_occurred = True # Mark as error if it was expected but didn't happen
                error_message = "Expected an error, but program executed successfully."
        except (LexerError, ParserError, InterpreterError) as e:
            error_occurred = True
            error_message = str(e)
            if "error_expected" in test_case and test_case["error_expected"]:
                if test_case.get("error_message_contains") and test_case["error_message_contains"] not in error_message:
                    print(f"FAIL: Error message did not contain expected substring.")
                    print(f"  Expected substring: '{test_case['error_message_contains']}'")
                    print(f"  Actual error: {error_message}")
                else:
                    print("PASS: Expected error occurred.")
                    passed_tests += 1
                continue # Move to next test
            else:
                print(f"FAIL: Unexpected error occurred.")
                print(f"  Error: {error_message}")
                continue # Move to next test
        except Exception as e:
            error_occurred = True
            error_message = f"An unexpected Python exception occurred: {type(e).__name__}: {e}"
            print(f"FAIL: Unexpected Python exception.")
            print(f"  Error: {error_message}")
            continue

        if error_occurred:
            print(f"FAIL: {error_message}")
        elif actual_output.strip() == test_case["expected_output"].strip():
            print("PASS")
            passed_tests += 1
        else:
            print("FAIL: Output mismatch.")
            print(f"  Expected:\n'{test_case['expected_output'].strip()}'")
            print(f"  Actual:\n'{actual_output.strip()}'")
    
    print(f"\n--- Test Summary ---")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

# The main function for command-line execution is kept, but not called in this tool_code block.
# It would be used if this script were run directly from a terminal.
def main():
    parser = argparse.ArgumentParser(description="C-like language interpreter.")
    parser.add_argument("file", nargs="?", help="Path to the program file to execute.")
    parser.add_argument("--test", action="store_true", help="Run embedded test suite.")
    parser.add_argument("--syntax", action="store_true", help="Print language syntax documentation.")

    args = parser.parse_args()

    if args.syntax:
        print(LANGUAGE_SPECIFICATION)
        sys.exit(0)

    if args.test:
        run_tests()
        sys.exit(0)

    if args.file:
        try:
            with open(args.file, 'r') as f:
                program_code = f.read()
            output = interpreter_main(program_code)
            if output:
                print(output)
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        except (LexerError, ParserError, InterpreterError) as e:
            print(f"Execution Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during execution: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("No file provided. Use --test to run tests or --syntax for documentation.", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

# Call run_tests directly for the tool_code execution
run_tests()