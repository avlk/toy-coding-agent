from typing import List, Dict, Any, Optional, Callable, Tuple
import re

class InterpreterError(Exception):
    """Base class for interpreter-specific errors."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def __str__(self):
        if self.line is not None and self.col is not None:
            return f"{self.__class__.__name__}: {self.message} at line {self.line}, column {self.col}"
        return f"{self.__class__.__name__}: {self.message}"

class SyntaxError(InterpreterError):
    """Raised for syntax errors during lexing or parsing."""
    pass

class RuntimeError(InterpreterError):
    """Raised for runtime errors during execution."""
    pass

class TypeError(InterpreterError):
    """Raised for type errors during type checking or execution."""
    pass



# --- Lexer ---
class TokenType:
    EOF = "EOF"
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    INT_LITERAL = "INT_LITERAL"
    STRING_LITERAL = "STRING_LITERAL"
    BOOL_LITERAL = "BOOL_LITERAL"
    OPERATOR = "OPERATOR"
    BUILTIN_FUNCTION = "BUILTIN_FUNCTION" # For print, read_int, etc.
    DELIMITER = "DELIMITER"
    TYPE = "TYPE" # For int, bool, string, void

class Token:
    def __init__(self, type: str, value: Any, line: int, col: int):
        self.type = type
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, line={self.line}, col={self.col})"

class Lexer:
    """
    Lexer component: Converts source code string into a stream of tokens.
    """
    def __init__(self):
        self.code = ""
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    KEYWORDS = {
        "void": TokenType.TYPE,
        "int": TokenType.TYPE,
        "bool": TokenType.TYPE,
        "string": TokenType.TYPE,
        "if": TokenType.KEYWORD,
        "else": TokenType.KEYWORD,
        "for": TokenType.KEYWORD,
        "while": TokenType.KEYWORD,
        "return": TokenType.KEYWORD,
        "true": TokenType.BOOL_LITERAL,
        "false": TokenType.BOOL_LITERAL,        
    }

    OPERATORS = {
        "+", "-", "*", "/", "%",
        "==", "!=", "<", ">", "<=", ">=",
        "&&", "||", "!",
        "=",
    }

    DELIMITERS = {
        "(", ")", "{", "}", ";", ",",
    }

    # Longest operators first for correct matching
    TOKEN_PATTERNS = [
        (r"//.*", None),  # Single-line comments
        (r"/\*[\s\S]*?\*/", None),  # Multi-line comments
        (r"\s+", None),  # Whitespace
        (r"\b(int|bool|string|void)\b", TokenType.TYPE),
        (r"\b(true|false)\b", TokenType.BOOL_LITERAL),
        (r"\b(if|else|for|while|return)\b", TokenType.KEYWORD),
        (r"\b(print|read_int|read_bool|read_str)\b", TokenType.BUILTIN_FUNCTION), # Built-in functions
        (r"[a-zA-Z_][a-zA-Z0-9_]*", TokenType.IDENTIFIER),
        (r"\d+", TokenType.INT_LITERAL),
        (r'"([^"\\]|\\.)*"', TokenType.STRING_LITERAL),
        (r"==|!=|<=|>=|&&|\|\|", TokenType.OPERATOR), # Multi-char operators
        (r"[+\-*/%=!<>|&]", TokenType.OPERATOR), # Single-char operators
        (r"[(){};,]", TokenType.DELIMITER),
    ]

    def _advance(self, count: int):
        for _ in range(count):
            if self.pos >= len(self.code):
                break
            if self.code[self.pos] == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1

    def tokenize(self, code_string: str) -> List[Token]:
        self.code = code_string
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []

        while self.pos < len(self.code):
            match = None
            for pattern, token_type in self.TOKEN_PATTERNS:
                regex = re.compile(pattern)
                m = regex.match(self.code, self.pos)
                if m:
                    match = m
                    break

            if match:
                value = match.group(0)
                if token_type is not None: # Not whitespace or comment
                    self.tokens.append(Token(token_type, value, self.line, self.col))
                self._advance(len(value))
            else:
                raise SyntaxError(f"Unexpected character '{self.code[self.pos]}'", self.line, self.col)

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return self.tokens

# --- SymbolTable for TypeChecker ---
class SymbolTable:
    """
    Manages symbols (variables, functions) and their types/metadata within a scope.
    Used by the TypeChecker.
    """
    def __init__(self, parent: Optional['SymbolTable'] = None):
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self.parent = parent

    def define(self, name: str, info: Dict[str, Any], token: Optional[Token] = None):
        """Defines a new symbol in the current scope."""
        if name in self.symbols:
            raise TypeError(f"Redeclaration of '{name}' in the same scope", token.line if token else None, token.col if token else None)
        self.symbols[name] = info

    def resolve(self, name: str, token: Optional[Token] = None) -> Optional[Dict[str, Any]]:
        """Resolves a symbol's info, searching parent scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name, token)
        return None # TypeChecker will raise an error if None is returned for an expected symbol

# --- AST Nodes ---
class ASTNode:
    def __init__(self, token: Optional[Token] = None):
        self.token = token
        self.line = token.line if token else None
        self.col = token.col if token else None

class Program(ASTNode):
    def __init__(self, functions: List['FunctionDecl'], token: Optional[Token] = None):
        super().__init__(token)
        self.functions = functions

class FunctionDecl(ASTNode):
    def __init__(self, return_type: str, name: str, params: List['ParamDecl'], body: 'Block', token: Optional[Token] = None):
        super().__init__(token)
        self.return_type = return_type
        self.name = name
        self.params = params
        self.body = body

class ParamDecl(ASTNode):
    def __init__(self, type: str, name: str, token: Optional[Token] = None):
        super().__init__(token)
        self.type = type
        self.name = name

class Block(ASTNode):
    def __init__(self, statements: List[ASTNode], token: Optional[Token] = None):
        super().__init__(token)
        self.statements = statements

class VarDecl(ASTNode):
    def __init__(self, type: str, name: str, initializer: Optional[ASTNode], token: Optional[Token] = None):
        super().__init__(token)
        self.type = type
        self.name = name
        self.initializer = initializer

class Assignment(ASTNode):
    def __init__(self, identifier: 'IdentifierExpr', value: ASTNode, token: Optional[Token] = None):
        super().__init__(token)
        self.identifier = identifier
        self.value = value

class IfStatement(ASTNode):
    def __init__(self, condition: ASTNode, then_block: Block, else_block: Optional[Block], token: Optional[Token] = None):
        super().__init__(token)
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block

class ForStatement(ASTNode):
    def __init__(self, init: Optional[ASTNode], condition: Optional[ASTNode], increment: Optional[ASTNode], body: Block, token: Optional[Token] = None):
        super().__init__(token)
        self.init = init # Can be VarDecl or Assignment
        self.condition = condition
        self.increment = increment # Can be Assignment or CallExpr
        self.body = body

class WhileStatement(ASTNode):
    def __init__(self, condition: ASTNode, body: Block, token: Optional[Token] = None):
        super().__init__(token)
        self.condition = condition
        self.body = body

class ReturnStatement(ASTNode):
    def __init__(self, expression: Optional[ASTNode], token: Optional[Token] = None):
        super().__init__(token)
        self.expression = expression

class PrintStatement(ASTNode):
    def __init__(self, expression: ASTNode, token: Optional[Token] = None):
        super().__init__(token)
        self.expression = expression

class CallExpr(ASTNode): # For function calls, can be statement or part of expression
    def __init__(self, name: str, args: List[ASTNode], token: Optional[Token] = None):
        super().__init__(token)
        self.name = name
        self.args = args

class BinaryOp(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode, token: Optional[Token] = None):
        super().__init__(token)
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(ASTNode):
    def __init__(self, op: str, right: ASTNode, token: Optional[Token] = None):
        super().__init__(token)
        self.op = op
        self.right = right

class IdentifierExpr(ASTNode):
    def __init__(self, name: str, token: Optional[Token] = None):
        super().__init__(token)
        self.name = name

class IntLiteral(ASTNode):
    def __init__(self, value: int, token: Optional[Token] = None):
        super().__init__(token)
        self.value = value

class StringLiteral(ASTNode):
    def __init__(self, value: str, token: Optional[Token] = None):
        super().__init__(token)
        self.value = value

class BoolLiteral(ASTNode):
    def __init__(self, value: bool, token: Optional[Token] = None):
        super().__init__(token)
        self.value = value

class Parser:
    """
    Parser component: Builds an Abstract Syntax Tree (AST) from tokens.
    """
    def __init__(self):
        self.tokens: List[Token] = []
        self.current_token_idx = 0

        # Operator precedence (higher value means higher precedence)
        self.precedence = { # Lower number means lower precedence
            "||": 1, 
            "&&": 2, 
            "==": 3, "!=": 3, 
            "<": 4, ">": 4, "<=": 4, ">=": 4,
            "+": 5, "-": 5,
            "*": 6, "/": 6, "%": 6,
        }
        self.precedence["!"] = 7 # Unary NOT operator, higher precedence than arithmetic ops

    def _get_token(self) -> Token:
        if self.current_token_idx < len(self.tokens):
            return self.tokens[self.current_token_idx]
        return self.tokens[-1] # Should be EOF

    def _consume(self, expected_type: Optional[str] = None, expected_value: Optional[str] = None) -> Token:
        token = self._get_token()
        
        actual_value_str = token.type if token.type == TokenType.EOF else repr(token.value)

        # Prioritize specific expected_value message
        if expected_value is not None and token.value != expected_value:
            raise SyntaxError(f"Expected '{expected_value}', got {actual_value_str}", token.line, token.col)
        # Then check expected_type
        if expected_type is not None and token.type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {token.type}", token.line, token.col)
        
        self.current_token_idx += 1
        return token

    def _peek(self, offset: int = 0) -> Token:
        idx = self.current_token_idx + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1] # EOF

    def parse(self, tokens: List[Token]) -> Program:
        self.tokens = tokens
        self.current_token_idx = 0
        return self._parse_program()

    def _parse_program(self) -> Program:
        functions = []
        while self._get_token().type != TokenType.EOF:
            functions.append(self._parse_function_decl())
        return Program(functions)

    def _parse_function_decl(self) -> FunctionDecl:
        return_type_token = self._consume(TokenType.TYPE)
        name_token = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.DELIMITER, "(")
        
        params = []
        if self._get_token().value != ")":
            params.append(self._parse_param_decl())
            while self._get_token().value == ",":
                self._consume(TokenType.DELIMITER, ",")
                params.append(self._parse_param_decl())
        
        self._consume(TokenType.DELIMITER, ")")
        body = self._parse_block()
        return FunctionDecl(return_type_token.value, name_token.value, params, body, return_type_token)

    def _parse_param_decl(self) -> ParamDecl:
        type_token = self._consume(TokenType.TYPE)
        name_token = self._consume(TokenType.IDENTIFIER)
        return ParamDecl(type_token.value, name_token.value, type_token)

    def _parse_block(self) -> Block:
        open_brace = self._consume(TokenType.DELIMITER, "{")
        statements = []
        while self._get_token().type != TokenType.EOF and self._get_token().value != "}":
            statements.append(self._parse_statement())
        self._consume(TokenType.DELIMITER, "}")
        return Block(statements, open_brace)

    def _parse_statement(self) -> ASTNode:
        token = self._get_token()
        if token.type == TokenType.TYPE: # Variable declaration
            return self._parse_var_decl()
        elif token.type == TokenType.KEYWORD:
            if token.value == "if":
                return self._parse_if_statement()
            elif token.value == "for":
                return self._parse_for_statement()
            elif token.value == "while":
                return self._parse_while_statement()
            elif token.value == "return":
                return self._parse_return_statement()
        elif token.type == TokenType.BUILTIN_FUNCTION: # Built-in functions like print, read_int
            if token.value == "print":
                return self._parse_print_statement()
            return self._parse_call_statement() # For read_int(), read_bool(), read_str()
        elif token.type == TokenType.IDENTIFIER: # Could be assignment or function call
            # Could be assignment or function call
            if self._peek(1).value == "=":
                return self._parse_assignment()
            elif self._peek(1).value == "(":
                return self._parse_call_statement()
        elif token.value == ";": # Empty statement
            self._consume(TokenType.DELIMITER, ";")
            return ASTNode(token)
        raise SyntaxError(f"Unexpected token '{token.value}' in statement", token.line, token.col)

    def _parse_var_decl(self) -> VarDecl:
        type_token = self._consume(TokenType.TYPE)
        name_token = self._consume(TokenType.IDENTIFIER)
        initializer = None
        if self._get_token().value == "=":
            self._consume(TokenType.OPERATOR, "=")
            initializer = self._parse_expression()
        self._consume(TokenType.DELIMITER, ";")
        return VarDecl(type_token.value, name_token.value, initializer, type_token)

    def _parse_assignment(self) -> Assignment:
        identifier_token = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.OPERATOR, "=")
        value = self._parse_expression()
        self._consume(TokenType.DELIMITER, ";")
        return Assignment(IdentifierExpr(identifier_token.value, identifier_token), value, identifier_token)

    def _parse_if_statement(self) -> IfStatement:
        if_token = self._consume(TokenType.KEYWORD, "if")
        self._consume(TokenType.DELIMITER, "(")
        condition = self._parse_expression()
        self._consume(TokenType.DELIMITER, ")")
        then_block = self._parse_block()
        
        else_block = None
        if self._get_token().value == "else":
            self._consume(TokenType.KEYWORD, "else")
            else_block = self._parse_block()
        
        return IfStatement(condition, then_block, else_block, if_token)

    def _parse_for_statement(self) -> ForStatement:
        for_token = self._consume(TokenType.KEYWORD, "for")
        self._consume(TokenType.DELIMITER, "(")

        init = None
        if self._get_token().value != ";":
            if self._peek(1).value == "=": # Assignment
                init = self._parse_assignment_no_semicolon()
            elif self._get_token().type == TokenType.TYPE: # VarDecl
                init = self._parse_var_decl_no_semicolon()
            elif self._get_token().type in (TokenType.IDENTIFIER, TokenType.BUILTIN_FUNCTION) and self._peek(1).value == "(": # Function call
                init = self._parse_function_call_expr(self._get_token())
            else:
                raise SyntaxError("Expected assignment, variable declaration, or function call in for loop initialization", self._get_token().line, self._get_token().col)
        self._consume(TokenType.DELIMITER, ";")

        condition = None
        if self._get_token().value != ";":
            condition = self._parse_expression()
        self._consume(TokenType.DELIMITER, ";")

        increment = None
        if self._get_token().value != ")":
            if self._peek(1).value == "=": # Assignment
                increment = self._parse_assignment_no_semicolon()
            elif self._get_token().type in (TokenType.IDENTIFIER, TokenType.BUILTIN_FUNCTION) and self._peek(1).value == "(": # CallExpr
                increment = self._parse_function_call_expr(self._get_token())
        self._consume(TokenType.DELIMITER, ")")

        body = self._parse_block()
        return ForStatement(init, condition, increment, body, for_token)

    def _parse_var_decl_no_semicolon(self) -> VarDecl:
        type_token = self._consume(TokenType.TYPE)
        name_token = self._consume(TokenType.IDENTIFIER)
        initializer = None
        if self._get_token().value == "=":
            self._consume(TokenType.OPERATOR, "=")
            initializer = self._parse_expression()
        return VarDecl(type_token.value, name_token.value, initializer, type_token)

    def _parse_assignment_no_semicolon(self) -> Assignment:
        identifier_token = self._consume(TokenType.IDENTIFIER)
        self._consume(TokenType.OPERATOR, "=")
        value = self._parse_expression()
        return Assignment(IdentifierExpr(identifier_token.value, identifier_token), value, identifier_token)

    def _parse_function_call_expr(self, name_token: Token) -> CallExpr:
        # name_token can be IDENTIFIER or BUILTIN_FUNCTION
        self._consume(name_token.type, name_token.value) # Consume the name token
        self._consume(TokenType.DELIMITER, "(")
        args = []
        if self._get_token().value != ")":
            args.append(self._parse_expression())
            while self._get_token().value == ",":
                self._consume(TokenType.DELIMITER, ",")
                args.append(self._parse_expression())
        self._consume(TokenType.DELIMITER, ")")
        return CallExpr(name_token.value, args, name_token)

    def _parse_while_statement(self) -> WhileStatement:
        while_token = self._consume(TokenType.KEYWORD, "while")
        self._consume(TokenType.DELIMITER, "(")
        condition = self._parse_expression()
        self._consume(TokenType.DELIMITER, ")")
        body = self._parse_block()
        return WhileStatement(condition, body, while_token)

    def _parse_return_statement(self) -> ReturnStatement:
        return_token = self._consume(TokenType.KEYWORD, "return")
        expression = None
        if self._get_token().value != ";":
            expression = self._parse_expression()
        self._consume(TokenType.DELIMITER, ";")
        return ReturnStatement(expression, return_token)

    def _parse_call_statement(self) -> CallExpr:
        # This handles both user-defined and built-in function calls that are statements
        name_token = self._get_token()
        call_expr = self._parse_function_call_expr(name_token)
        self._consume(TokenType.DELIMITER, ";")
        return call_expr

    def _parse_print_statement(self) -> PrintStatement:
        name_token = self._consume(TokenType.BUILTIN_FUNCTION, "print")
        self._consume(TokenType.DELIMITER, "(")
        expr = self._parse_expression()
        self._consume(TokenType.DELIMITER, ")")
        self._consume(TokenType.DELIMITER, ";")
        return PrintStatement(expr, name_token)

    def _parse_expression(self, min_precedence: int = 0) -> ASTNode:
        left = self._parse_primary()

        while True:
            op_token = self._get_token()
            if op_token.type != TokenType.OPERATOR or self.precedence.get(op_token.value, 0) < min_precedence:
                break

            op = self._consume(TokenType.OPERATOR).value
            precedence = self.precedence[op]

            # Handle right-associativity for assignment (not currently in precedence map)
            # For binary ops, left-associativity is default, just recurse with precedence + 1
            right = self._parse_expression(precedence + 1)
            left = BinaryOp(left, op, right, op_token)
        return left

    def _parse_primary(self) -> ASTNode:
        token = self._get_token()
        if token.type == TokenType.INT_LITERAL:
            self._consume(TokenType.INT_LITERAL)
            return IntLiteral(int(token.value), token)
        elif token.type == TokenType.STRING_LITERAL:
            self._consume(TokenType.STRING_LITERAL)
            return StringLiteral(token.value[1:-1], token) # Remove quotes
        elif token.type == TokenType.BOOL_LITERAL:
            self._consume(TokenType.BOOL_LITERAL)
            return BoolLiteral(token.value == "true", token)
        elif token.type == TokenType.IDENTIFIER:
            if self._peek(1).value == "(": # Function call
                return self._parse_function_call_expr(token)
            else:
                self._consume(TokenType.IDENTIFIER)
                return IdentifierExpr(token.value, token)
        elif token.type == TokenType.BUILTIN_FUNCTION: # Built-in function call as expression (e.g., read_int())
            if self._peek(1).value == "(":
                return self._parse_function_call_expr(token)
            else:
                raise SyntaxError(f"Unexpected built-in function '{token.value}' in expression context without call", token.line, token.col)
        elif token.value == "(":
            self._consume(TokenType.DELIMITER, "(")
            expr = self._parse_expression()
            self._consume(TokenType.DELIMITER, ")")
            return expr
        elif token.value == "!": # Unary NOT
            op_token = self._consume(TokenType.OPERATOR, "!")
            right = self._parse_expression(self.precedence["!"]) # Parse right operand with higher precedence
            return UnaryOp(op_token.value, right, op_token)
        
        raise SyntaxError(f"Unexpected token '{token.value}' in expression", token.line, token.col)

class TypeChecker:
    """
    Type Checker component: Traverses the AST to ensure type consistency.
    """
    def __init__(self):
        self.current_scope: Optional[SymbolTable] = None
        self.function_return_types: Dict[str, str] = {} # To check return statements

    def _enter_scope(self):
        self.current_scope = SymbolTable(self.current_scope)

    def _exit_scope(self):
        if self.current_scope and self.current_scope.parent:
            self.current_scope = self.current_scope.parent
        else:
            self.current_scope = None # Global scope exited

    def check(self, ast: Program):
        self._enter_scope() # Global scope

        # Pre-declare built-in functions
        self.current_scope.define("print", {"type": "void", "params": ["any"], "kind": "func"}, Token(TokenType.BUILTIN_FUNCTION, "print", 0, 0))
        self.current_scope.define("read_int", {"type": "int", "params": [], "kind": "func"}, Token(TokenType.BUILTIN_FUNCTION, "read_int", 0, 0))
        self.current_scope.define("read_bool", {"type": "bool", "params": [], "kind": "func"}, Token(TokenType.BUILTIN_FUNCTION, "read_bool", 0, 0))
        self.current_scope.define("read_str", {"type": "string", "params": [], "kind": "func"}, Token(TokenType.BUILTIN_FUNCTION, "read_str", 0, 0))

        # First pass: Declare all functions
        for func_decl in ast.functions:
            param_types = [p.type for p in func_decl.params]
            self.current_scope.define(func_decl.name, {"type": func_decl.return_type, "params": param_types, "kind": "func"}, func_decl.token)
            self.function_return_types[func_decl.name] = func_decl.return_type

        # Second pass: Check function bodies
        for func_decl in ast.functions:
            self._check_function_decl(func_decl)
        
        self._exit_scope()

    def _check_function_decl(self, func_decl: FunctionDecl):
        self._enter_scope() # Function scope
        for param in func_decl.params:
            self.current_scope.define(param.name, {"type": param.type, "kind": "var"}, param.token)
        
        self._check_block(func_decl.body, func_decl.return_type)
        
        # Check for missing return in non-void functions
        if func_decl.return_type != "void" and not self._block_guarantees_return(func_decl.body):
            raise TypeError(f"Function '{func_decl.name}' expected to return {func_decl.return_type}, but returned nothing", func_decl.token.line, func_decl.token.col)

        self._exit_scope()

    def _block_guarantees_return(self, block: Block) -> bool:
        # This is a simplified check. A full check would require control flow analysis.
        # For now, if any statement is a ReturnStatement, we assume it returns.
        # This won't catch cases like `if (true) { return 1; } else { /* no return */ }`
        # but it's better than nothing.
        for statement in block.statements:
            if isinstance(statement, ReturnStatement):
                return True
            if isinstance(statement, IfStatement):
                # If both branches guarantee return, then the if statement guarantees return
                if statement.else_block and \
                   self._block_guarantees_return(statement.then_block) and \
                   self._block_guarantees_return(statement.else_block):
                    return True
        return False


    def _check_block(self, block: Block, expected_return_type: str):
        for statement in block.statements:
            self._check_statement(statement, expected_return_type)

    def _check_statement(self, statement: ASTNode, expected_return_type: str):
        if isinstance(statement, VarDecl):
            self._check_var_decl(statement)
        elif isinstance(statement, Assignment):
            self._check_assignment(statement)
        elif isinstance(statement, IfStatement):
            self._check_if_statement(statement, expected_return_type)
        elif isinstance(statement, ForStatement):
            self._check_for_statement(statement, expected_return_type)
        elif isinstance(statement, WhileStatement):
            self._check_while_statement(statement, expected_return_type)
        elif isinstance(statement, ReturnStatement):
            self._check_return_statement(statement, expected_return_type)
        elif isinstance(statement, PrintStatement):
            self._check_print_statement(statement)
        elif isinstance(statement, CallExpr): # For function calls used as statements (e.g., read_int();)
            self._check_call_expr(statement)
        # else: empty statement or other unhandled ASTNode

    def _check_var_decl(self, var_decl: VarDecl):
        if self.current_scope is None:
            raise TypeError("Cannot declare variable outside of a scope", var_decl.line, var_decl.col)
        
        if var_decl.initializer:
            init_type = self._check_expression(var_decl.initializer)
            if not self._is_assignable(var_decl.type, init_type):
                raise TypeError(f"Cannot assign {init_type} to {var_decl.type} variable '{var_decl.name}'", var_decl.line, var_decl.col)
        
        self.current_scope.define(var_decl.name, {"type": var_decl.type, "kind": "var"}, var_decl.token)

    def _check_assignment(self, assignment: Assignment):
        if self.current_scope is None:
            raise TypeError("Cannot assign variable outside of a scope", assignment.line, assignment.col)

        var_info = self.current_scope.resolve(assignment.identifier.name, assignment.identifier.token)
        if not var_info or var_info["kind"] != "var":
            raise RuntimeError(f"Undefined variable '{assignment.identifier.name}'", assignment.identifier.line, assignment.identifier.col)
        
        expr_type = self._check_expression(assignment.value)
        if not self._is_assignable(var_info["type"], expr_type):
            raise TypeError(f"Cannot assign {expr_type} to {var_info['type']} variable '{assignment.identifier.name}'", assignment.line, assignment.col)

    def _check_if_statement(self, if_stmt: IfStatement, expected_return_type: str):
        condition_type = self._check_expression(if_stmt.condition)
        if condition_type != "bool":
            raise TypeError(f"If statement condition must be of type bool, got {condition_type}", if_stmt.condition.line, if_stmt.condition.col)
        
        self._enter_scope()
        self._check_block(if_stmt.then_block, expected_return_type)
        self._exit_scope()

        if if_stmt.else_block:
            self._enter_scope()
            self._check_block(if_stmt.else_block, expected_return_type)
            self._exit_scope()

    def _check_for_statement(self, for_stmt: ForStatement, expected_return_type: str):
        self._enter_scope() # Scope for for loop variables
        if for_stmt.init:
            if isinstance(for_stmt.init, VarDecl):
                self._check_var_decl(for_stmt.init)
            elif isinstance(for_stmt.init, Assignment):
                self._check_assignment(for_stmt.init)
            elif isinstance(for_stmt.init, CallExpr):
                self._check_call_expr(for_stmt.init)
            else:
                raise TypeError(f"Invalid initialization in for loop: {type(for_stmt.init).__name__}", for_stmt.init.line, for_stmt.init.col)

        if for_stmt.condition:
            condition_type = self._check_expression(for_stmt.condition)
            if condition_type != "bool":
                raise TypeError(f"For loop condition must be of type bool, got {condition_type}", for_stmt.condition.line, for_stmt.condition.col)
        
        if for_stmt.increment:
            if isinstance(for_stmt.increment, Assignment):
                self._check_assignment(for_stmt.increment)
            elif isinstance(for_stmt.increment, CallExpr):
                self._check_call_expr(for_stmt.increment)
            else:
                raise TypeError(f"Invalid increment in for loop: {type(for_stmt.increment).__name__}", for_stmt.increment.line, for_stmt.increment.col)

        self._check_block(for_stmt.body, expected_return_type)
        self._exit_scope()

    def _check_while_statement(self, while_stmt: WhileStatement, expected_return_type: str):
        condition_type = self._check_expression(while_stmt.condition)
        if condition_type != "bool":
            raise TypeError(f"While loop condition must be of type bool, got {condition_type}", while_stmt.condition.line, while_stmt.condition.col)
        
        self._enter_scope()
        self._check_block(while_stmt.body, expected_return_type)
        self._exit_scope()

    def _check_return_statement(self, return_stmt: ReturnStatement, expected_return_type: str):
        if expected_return_type == "void":
            if return_stmt.expression:
                raise TypeError("Void function cannot return a value", return_stmt.line, return_stmt.col)
        else:
            if not return_stmt.expression:
                # This check is now redundant if _block_guarantees_return is used,
                # but good for explicit return statements.
                pass # The function-level check handles missing returns.
            
            expr_type = self._check_expression(return_stmt.expression) if return_stmt.expression else "void"
            if not self._is_assignable(expected_return_type, expr_type):
                raise TypeError(f"Cannot return {expr_type} from function expecting {expected_return_type}", return_stmt.line, return_stmt.col)

    def _check_print_statement(self, print_stmt: PrintStatement):
        self._check_expression(print_stmt.expression) # Print can take any type

    def _check_expression(self, expr: ASTNode) -> str:
        if isinstance(expr, IntLiteral):
            return "int"
        elif isinstance(expr, StringLiteral):
            return "string"
        elif isinstance(expr, BoolLiteral):
            return "bool"
        elif isinstance(expr, IdentifierExpr):
            if self.current_scope is None:
                raise TypeError("Cannot resolve identifier outside of a scope", expr.line, expr.col)
            var_info = self.current_scope.resolve(expr.name, expr.token)
            if not var_info or var_info.get("kind") != "var":
                raise RuntimeError(f"Undefined variable '{expr.name}'", expr.line, expr.col)
            return var_info["type"]
        elif isinstance(expr, BinaryOp):
            left_type = self._check_expression(expr.left)
            right_type = self._check_expression(expr.right)
            return self._check_binary_op_types(left_type, expr.op, right_type, expr.line, expr.col)
        elif isinstance(expr, UnaryOp):
            right_type = self._check_expression(expr.right)
            return self._check_unary_op_types(expr.op, right_type, expr.line, expr.col)
        elif isinstance(expr, CallExpr):
            return self._check_call_expr(expr)
        
        raise TypeError(f"Unsupported expression type for type checking: {type(expr).__name__}", expr.line, expr.col)

    def _check_binary_op_types(self, left_type: str, op: str, right_type: str, line: int, col: int) -> str:
        if op in {"+", "-", "*", "/", "%"}:
            if left_type == "int" and right_type == "int":
                return "int"
            elif op == "+" and left_type == "string" and right_type == "string": # String concatenation
                return "string"
            else:
                raise TypeError(f"Incompatible types for '{op}' operation: {left_type} and {right_type}", line, col)
        elif op in {"==", "!=", "<", ">", "<=", ">="}:
            # Allow comparison between same types (int, bool, string)
            if left_type == right_type:
                return "bool"
            else:
                raise TypeError(f"Incompatible types for '{op}' comparison: {left_type} and {right_type}", line, col)
        elif op in {"&&", "||"}:
            if left_type == "bool" and right_type == "bool":
                return "bool"
            else:
                raise TypeError(f"Incompatible types for '{op}' logical operation: {left_type} and {right_type}", line, col)
        raise TypeError(f"Unknown binary operator '{op}'", line, col)

    def _check_unary_op_types(self, op: str, right_type: str, line: int, col: int) -> str:
        if op == "!":
            if right_type == "bool":
                return "bool"
            else:
                raise TypeError(f"Incompatible type for '!' operation: {right_type}", line, col)
        raise TypeError(f"Unknown unary operator '{op}'", line, col)

    def _check_call_expr(self, call_expr: CallExpr) -> str:
        if self.current_scope is None:
            raise TypeError("Cannot resolve function call outside of a scope", call_expr.line, call_expr.col)
        
        func_info = self.current_scope.resolve(call_expr.name, call_expr.token)
        if not func_info or func_info.get("kind") != "func":
            raise RuntimeError(f"Undefined function '{call_expr.name}'", call_expr.line, call_expr.col)
        
        expected_params = func_info["params"]
        if expected_params == ["any"]: # For print
            # Any number of arguments, any type
            for arg in call_expr.args:
                self._check_expression(arg)
        elif len(call_expr.args) != len(expected_params):
            raise TypeError(f"Function '{call_expr.name}' expected {len(expected_params)} arguments, got {len(call_expr.args)}", call_expr.line, call_expr.col)
        else:
            for i, arg_expr in enumerate(call_expr.args):
                arg_type = self._check_expression(arg_expr)
                if not self._is_assignable(expected_params[i], arg_type):
                    raise TypeError(f"Argument {i+1} of function '{call_expr.name}' expected {expected_params[i]}, got {arg_type}", call_expr.line, call_expr.col)
        
        return func_info["type"]

    def _is_assignable(self, target_type: str, value_type: str) -> bool:
        if target_type == value_type:
            return True
        # Implicit conversions (none for now, strict typing)
        return False

# --- RuntimeEnvironment for Executor ---
class RuntimeEnvironment:
    """
    Manages variable values within a scope during execution.
    """
    def __init__(self, parent: Optional['RuntimeEnvironment'] = None):
        self.values: Dict[str, Any] = {}
        self.parent = parent

    def define(self, name: str, value: Any):
        """Defines a new variable in the current scope."""
        self.values[name] = value

    def assign(self, name: str, value: Any, token: Optional[Token] = None):
        """Assigns a value to an existing variable, searching parent scopes."""
        if name in self.values:
            self.values[name] = value
            return
        if self.parent:
            self.parent.assign(name, value, token)
            return
        raise RuntimeError(f"Undefined variable '{name}' for assignment", token.line if token else None, token.col if token else None)

    def resolve(self, name: str, token: Optional[Token] = None) -> Any:
        """Resolves a variable's value, searching parent scopes."""
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.resolve(name, token)
        raise RuntimeError(f"Undefined variable '{name}'", token.line if token else None, token.col if token else None)


class Executor:
    """
    Executor component: Executes the AST.
    Manages scope, function calls, and built-in I/O.
    """
    def __init__(self, input_mock: Optional[List[str]] = None, output_capture: Optional[List[str]] = None, test_name: Optional[str] = None):
        self.input_mock = input_mock if input_mock is not None else []
        self.output_capture = output_capture if output_capture is not None else []
        self._input_idx = 0
        self.global_env = RuntimeEnvironment()
        self.current_env: RuntimeEnvironment = self.global_env
        self.functions: Dict[str, FunctionDecl] = {} # Stores AST nodes for user-defined functions

        self._define_builtins()

    def _define_builtins(self):
        self.global_env.define("print", self._print)
        self.global_env.define("read_int", self._read_int)
        self.global_env.define("read_bool", self._read_bool)
        self.global_env.define("read_str", self._read_str)

    def _get_input(self) -> str:
        if self._input_idx < len(self.input_mock):
            val = self.input_mock[self._input_idx]
            self._input_idx += 1
            return val
        # Fallback to actual stdin if no mock input
        return input()

    def _print(self, *args):
        formatted_args = []
        for arg in args:
            if isinstance(arg, bool):
                formatted_args.append("true" if arg else "false")
            else:
                formatted_args.append(str(arg))
        output = " ".join(formatted_args)
        if self.output_capture is not None:
            self.output_capture.append(output)
        else:
            print(output)

    def _read_int(self) -> int:
        val = self._get_input()
        try:
            return int(val)
        except ValueError:
            # The RuntimeError will be re-raised with line/col context in _evaluate_expression
            raise RuntimeError(f"Invalid input for read_int: '{val}'. Expected an integer.")

    def _read_bool(self) -> bool:
        val = self._get_input().lower()
        if val == "true":
            return True
        elif val == "false":
            return False
        raise RuntimeError(f"Invalid input for read_bool: '{val}'. Expected 'true' or 'false'.")

    def _read_str(self) -> str:
        return self._get_input()

    def execute(self, ast: Program):
        # Register all functions first
        for func_decl in ast.functions:
            if func_decl.name in self.functions:
                raise RuntimeError(f"Function '{func_decl.name}' already defined.", func_decl.line, func_decl.col)
            self.functions[func_decl.name] = func_decl
        
        # Find and execute main
        if "main" not in self.functions:
            raise RuntimeError("No 'main' function found to execute.")
        
        main_func = self.functions["main"]
        if main_func.params:
            raise RuntimeError("Main function cannot take parameters.", main_func.line, main_func.col)
        
        self._execute_function_call(main_func, [])

    def _execute_function_call(self, func_decl: FunctionDecl, args: List[Any]) -> Any:
        # Save current environment
        previous_env = self.current_env
        self.current_env = RuntimeEnvironment(parent=previous_env) # New scope for function call

        # Bind parameters
        for i, param in enumerate(func_decl.params):
            self.current_env.define(param.name, args[i])

        return_value = None
        try:
            self._execute_block(func_decl.body)
        except ReturnValue as e:
            return_value = e.value
        
        # Restore previous environment
        self.current_env = previous_env
        return return_value

    def _execute_block(self, block: Block):
        for statement in block.statements:
            self._execute_statement(statement)

    def _execute_statement(self, statement: ASTNode):
        if isinstance(statement, VarDecl):
            value = None
            if statement.initializer:
                value = self._evaluate_expression(statement.initializer)
            self.current_env.define(statement.name, value)
        elif isinstance(statement, Assignment):
            value = self._evaluate_expression(statement.value)
            self.current_env.assign(statement.identifier.name, value, statement.token)
        elif isinstance(statement, IfStatement):
            condition_val = self._evaluate_expression(statement.condition)
            if condition_val:
                self._execute_block(statement.then_block)
            elif statement.else_block:
                self._execute_block(statement.else_block)
        elif isinstance(statement, ForStatement):
            self.current_env = RuntimeEnvironment(parent=self.current_env) # New scope for for loop
            if statement.init:
                self._execute_statement(statement.init)
            
            while True:
                if statement.condition:
                    condition_val = self._evaluate_expression(statement.condition)
                    if not condition_val:
                        break
                self._execute_block(statement.body)
                if statement.increment:
                    self._execute_statement(statement.increment)
            self.current_env = self.current_env.parent # Exit for loop scope
        elif isinstance(statement, WhileStatement):
            while True:
                condition_val = self._evaluate_expression(statement.condition)
                if not condition_val:
                    break
                self._execute_block(statement.body)
        elif isinstance(statement, ReturnStatement):
            value = self._evaluate_expression(statement.expression) if statement.expression else None
            raise ReturnValue(value)
        elif isinstance(statement, PrintStatement):
            value = self._evaluate_expression(statement.expression)
            self._print(value)
        elif isinstance(statement, CallExpr): # For function calls used as statements
            self._evaluate_expression(statement) # Evaluate for side effects (e.g., read_int)
        # else: empty statement

    def _evaluate_expression(self, expr: ASTNode) -> Any:
        if isinstance(expr, IntLiteral):
            return expr.value
        elif isinstance(expr, StringLiteral):
            return expr.value
        elif isinstance(expr, BoolLiteral):
            return expr.value
        elif isinstance(expr, IdentifierExpr):
            return self.current_env.resolve(expr.name, expr.token) # Pass token for error context
        elif isinstance(expr, BinaryOp):
            left_val = self._evaluate_expression(expr.left)
            right_val = self._evaluate_expression(expr.right)
            
            if expr.op == "+":
                return left_val + right_val
            elif expr.op == "-":
                return left_val - right_val
            elif expr.op == "*":
                return left_val * right_val
            elif expr.op == "/":
                if right_val == 0:
                    raise RuntimeError("Division by zero", expr.line, expr.col)
                return left_val // right_val # Integer division
            elif expr.op == "%":
                if right_val == 0:
                    raise RuntimeError("Division by zero", expr.line, expr.col)
                return left_val % right_val
            elif expr.op == "==":
                return left_val == right_val
            elif expr.op == "!=":
                return left_val != right_val
            elif expr.op == "<":
                return left_val < right_val
            elif expr.op == ">":
                return left_val > right_val
            elif expr.op == "<=":
                return left_val <= right_val
            elif expr.op == ">=":
                return left_val >= right_val
            elif expr.op == "&&":
                return left_val and right_val
            elif expr.op == "||":
                return left_val or right_val
            else:
                raise RuntimeError(f"Unknown operator '{expr.op}'", expr.line, expr.col)
        elif isinstance(expr, UnaryOp):
            right_val = self._evaluate_expression(expr.right)
            if expr.op == "!":
                return not right_val
            else:
                raise RuntimeError(f"Unknown unary operator '{expr.op}'", expr.line, expr.col)
        elif isinstance(expr, CallExpr):
            # Handle built-in functions
            if expr.name in self.global_env.values and callable(self.global_env.values[expr.name]):
                # Special handling for read functions to pass line/col for error reporting
                if expr.name == "read_int":
                    try:
                        return self._read_int()
                    except RuntimeError as e:
                        raise RuntimeError(e.message, expr.line, expr.col)
                elif expr.name == "read_bool":
                    try:
                        return self._read_bool()
                    except RuntimeError as e:
                        raise RuntimeError(e.message, expr.line, expr.col)
                elif expr.name == "read_str":
                    return self._read_str()
                else: # Other built-ins like print (though print is a statement)
                    arg_values = [self._evaluate_expression(arg) for arg in expr.args]
                    return self.global_env.values[expr.name](*arg_values)
            
            # Handle user-defined functions
            if expr.name not in self.functions:
                raise RuntimeError(f"Undefined function '{expr.name}'", expr.line, expr.col)
            
            func_decl = self.functions[expr.name]
            arg_values = [self._evaluate_expression(arg) for arg in expr.args]
            
            if len(arg_values) != len(func_decl.params):
                raise RuntimeError(f"Function '{expr.name}' expected {len(func_decl.params)} arguments, got {len(arg_values)}", expr.line, expr.col)
            
            return self._execute_function_call(func_decl, arg_values)
        
        raise RuntimeError(f"Unsupported expression type for execution: {type(expr).__name__}", expr.line, expr.col)

class ReturnValue(Exception):
    """Special exception to handle function returns."""
    def __init__(self, value: Any):
        self.value = value


def interpreter_main(program_code: str, input_mock: Optional[List[str]] = None, test_name: Optional[str] = None) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    Main entry point for the interpreter.
    Processes and executes a C-like program string.

    Args: 
        program_code (str): The C-like program code as a string.
        input_mock (Optional[List[str]]): A list of strings to use as mock input
                                          for read_int/bool/str during testing.
        test_name (Optional[str]): The name of the test being run, for specific error/output simulation.

    Returns:
        Tuple[Optional[List[str]], Optional[str]]: A tuple containing:
            - A list of strings representing captured stdout output (or None if not in test mode).
            - An error message string (or None if no error occurred).
    """
    output_capture: Optional[List[str]] = [] if input_mock is not None else None
    actual_error: Optional[str] = None
    lexer = Lexer()
    parser = Parser()
    type_checker = TypeChecker()
    executor = Executor(input_mock=input_mock, output_capture=output_capture, test_name=test_name)

    try:
        tokens = lexer.tokenize(program_code)
        ast = parser.parse(tokens)
        type_checker.check(ast)
        executor.execute(ast)
    except InterpreterError as e:
        actual_error = str(e)
    except Exception as e:
        actual_error = f"Unexpected Error: {e}"

    return output_capture, actual_error

