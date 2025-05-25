"""
Contains methods to lex strings/ files, breaking them into lists of tokens
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TokenType(Enum):
    """
    The various types of tokens, along with the regex string that matches them
    """

    OPEN_BRACKET = r"{"
    CLOSE_BRACKET = r"}"
    OPEN_PARENTHESIS = r"\("
    CLOSE_PARENTHESIS = r"\)"
    SEMICOLON = r";"
    RETURN = r"return\b"
    INT = r"int\b"
    IDENTIFIER = r"[a-zA-Z]\w*"
    INT_LITERAL = r"\d+"

    @classmethod
    def value_tokens(cls) -> dict["TokenType", type]:
        """
        Returns a dictionary of TokenTypes with the type of value each token type expects.

        TokenTypes without a value are not included
        """
        return {cls.IDENTIFIER: str, cls.INT_LITERAL: int}


TOKEN_REGEX = "|".join([token_type.value for token_type in TokenType])


@dataclass
class Token:
    """
    Contains a type and an optional value if the associated type has a value
    """

    token_type: TokenType
    value: Optional[str | int] = None

    def __post_init__(self):
        if self.token_type in TokenType.value_tokens():
            assert self.value is not None and isinstance(
                self.value, TokenType.value_tokens()[self.token_type]
            )


def lex_str(input_str: str) -> list[Token]:
    """
    Reads in a string and lexes it into a list of tokens
    """
    raw_tokens = re.findall(TOKEN_REGEX, input_str)
    tokens: list[Token] = []
    for raw_token in raw_tokens:
        for token_type in TokenType:
            if re.match(token_type.value, raw_token):
                value = None
                if token_type == TokenType.IDENTIFIER:
                    value = raw_token

                elif token_type == TokenType.INT_LITERAL:
                    value = int(raw_token)

                tokens.append(Token(token_type, value))
                break

    return tokens


def lex_file(filename: str) -> list[Token]:
    """
    Reads in a file and lexes it into a list of tokens
    """
    with open(filename, "r", encoding="UTF-8") as file:
        return lex_str(file.read())
