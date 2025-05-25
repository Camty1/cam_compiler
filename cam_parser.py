from dataclasses import dataclass
from typing import Iterator, Optional

from cam_lexer import Token, TokenType


@dataclass
class Expression:
    """
    Represents an expression in an AST tree
    """

    value: int

    @classmethod
    def parse(cls, tokens: Iterator[Token]) -> Optional["Expression"]:
        """
        Parse a string of tokens into an expression if it is valid
        """
        token = next(tokens)
        if token.token_type != TokenType.INT_LITERAL:
            return None

        assert token.value is not None and isinstance(
            token.value, TokenType.value_tokens()[token.token_type]
        )

        return Expression(token.value)

    def evaluate(self) -> int:
        """
        Evaluate the expression
        """
        return self.value


@dataclass
class Statement:
    """
    Represents a statement in an AST tree
    """

    expression: Expression

    @classmethod
    def parse(cls, tokens: Iterator[Token]) -> Optional["Statement"]:
        """
        Parse a string of tokens into an expression if it is valid
        """
        token = next(tokens)
        if token.token_type != TokenType.RETURN:
            return None

        expression = Expression.parse(tokens)
        if not expression:
            return None

        token = next(tokens)
        if token.token_type != TokenType.SEMICOLON:
            return None

        return Statement(expression)

    def compile(self) -> str:
        """
        Produce assembly of the statement
        """
        return f"    mov     w0, #{self.expression.evaluate()}\n    ret"


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
        token = next(tokens)
        if token.token_type != TokenType.INT:
            return None

        token = next(tokens)
        if token.token_type != TokenType.IDENTIFIER:
            return None
        name = token.value
        assert name and isinstance(name, TokenType.value_tokens()[token.token_type])

        token = next(tokens)
        if token.token_type != TokenType.OPEN_PARENTHESIS:
            return None

        token = next(tokens)
        if token.token_type != TokenType.CLOSE_PARENTHESIS:
            return None

        token = next(tokens)
        if token.token_type != TokenType.OPEN_BRACKET:
            return None

        statement = Statement.parse(tokens)
        if not statement:
            return None

        token = next(tokens)
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
