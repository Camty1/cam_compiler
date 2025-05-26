"""
Used to parse lexed tokens into AST trees, which can then be compiled into a program
"""

from dataclasses import dataclass
from typing import Iterator, Optional, Union

from cam_lexer import Token, TokenType, UnaryOperator


def safe_next(tokens: Iterator[Token]) -> Optional[Token]:
    """
    Gets the next token from an iterator if it exists, otherwise returns None
    """
    try:
        return next(tokens)
    except StopIteration:
        return None


@dataclass
class ConstantExpression:
    """
    Represents a constant integer in an AST tree
    """

    value: int

    def compile(self) -> str:
        """
        Return the expression as assembly
        """
        return f"    mov     w0, #{self.value}"


@dataclass
class UnaryOperatorExpression:
    """
    Represents a unary operator in an AST tree
    """

    operator: UnaryOperator
    expression: Union[ConstantExpression, "UnaryOperatorExpression"]

    def compile(self) -> Optional[str]:
        """
        Return the expression as assembly
        """
        compiled_expression = self.expression.compile()
        if not compiled_expression:
            return None

        if self.operator == UnaryOperator.NEGATION:
            return compiled_expression + "\n    neg     w0, w0"

        if self.operator == UnaryOperator.COMPLEMENT:
            return compiled_expression + "\n    mvn     w0, w0"

        if self.operator == UnaryOperator.NOT:
            return compiled_expression + "\n    cmp     w0, #0\n    cset    w0, eq"

        return None


@dataclass
class Expression:
    """
    Represents an expression in an AST tree
    """

    @classmethod
    def parse(
        cls, tokens: Iterator[Token]
    ) -> Optional[ConstantExpression | UnaryOperatorExpression]:
        """
        Parse a string of tokens into an expression if it is valid
        """
        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type == TokenType.INT_LITERAL:
            assert token.value is not None and isinstance(
                token.value, TokenType.value_tokens()[token.token_type]
            )
            return ConstantExpression(token.value)

        if token.token_type in TokenType.unary_operators():
            operator = TokenType.unary_operators()[token.token_type]
            expression = Expression.parse(tokens)
            if not expression:
                return None
            return UnaryOperatorExpression(operator, expression)
        return None


@dataclass
class Statement:
    """
    Represents a statement in an AST tree
    """

    expression: ConstantExpression | UnaryOperatorExpression

    @classmethod
    def parse(cls, tokens: Iterator[Token]) -> Optional["Statement"]:
        """
        Parse a string of tokens into an expression if it is valid
        """
        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.RETURN:
            return None

        expression = Expression.parse(tokens)
        if not expression:
            return None

        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.SEMICOLON:
            return None

        return Statement(expression)

    def compile(self) -> str:
        """
        Produce assembly of the statement
        """

        return self.expression.compile() + "\n    ret"


@dataclass
class Function:
    """
    Represents a function in an AST tree
    """

    name: str
    statement: Statement

    @classmethod
    def parse(cls, tokens: Iterator[Token]) -> Optional["Function"]:
        """
        Parses a string of tokens into a function if it is valid
        """
        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.INT:
            return None

        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.IDENTIFIER:
            return None
        name = token.value
        assert name and isinstance(name, TokenType.value_tokens()[token.token_type])

        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.OPEN_PARENTHESIS:
            return None

        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.CLOSE_PARENTHESIS:
            return None

        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.OPEN_BRACKET:
            return None

        statement = Statement.parse(tokens)
        if not statement:
            return None

        maybe_token = safe_next(tokens)
        if maybe_token is None:
            return None
        token = maybe_token
        if token.token_type != TokenType.CLOSE_BRACKET:
            return None

        return Function(name, statement)

    def compile(self) -> str:
        """
        Produces assembly of the function
        """
        header_str = f"    .globl _{self.name}\n_{self.name}:"
        statement_str = self.statement.compile()
        return "\n".join([header_str, statement_str])


@dataclass
class Program:
    """
    Represents a program in an AST tree
    """

    function: Function

    @classmethod
    def parse(cls, tokens: list[Token]) -> Optional["Program"]:
        """
        Parses a string of tokens into a program if they are valid
        """
        tokens_iterator = (token for token in tokens)
        result = Function.parse(tokens_iterator)

        if result:
            return Program(result)

        return None

    def compile(self) -> str:
        """
        Compiles the program to assembly
        """
        return self.function.compile()
