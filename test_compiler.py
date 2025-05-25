"""
Used for running pytest tests of the compiler
"""

from pathlib import Path

import pytest

from cam_lexer import Token, TokenType, lex_file
from cam_parser import Program

MAX_STAGE = 1


def valid_programs() -> list[Path]:
    """
    Used to get all valid programs for all stages up to and including MAX_STAGE
    """
    programs: list[Path] = []
    for stage in range(1, MAX_STAGE + 1):
        programs += [
            file
            for file in Path(f"./stage_{stage}/valid/").iterdir()
            if str(file)[-2:] == ".c"
        ]

    return programs


def invalid_programs() -> list[Path]:
    """
    Used to get all invalid programs for all stages up to and including MAX_STAGE
    """
    programs: list[Path] = []
    for stage in range(1, MAX_STAGE + 1):
        programs += [
            file
            for file in Path(f"./stage_{stage}/invalid/").iterdir()
            if str(file)[-2:] == ".c"
        ]

    return programs


def test_lex_return_2():
    """
    Tests the lexer on an example program (very simple) to see that it is behaving as expected.
    """
    test_file = "./stage_1/valid/return_2.c"

    assert lex_file(test_file) == [
        Token(TokenType.INT),
        Token(TokenType.IDENTIFIER, "main"),
        Token(TokenType.OPEN_PARENTHESIS),
        Token(TokenType.CLOSE_PARENTHESIS),
        Token(TokenType.OPEN_BRACKET),
        Token(TokenType.RETURN),
        Token(TokenType.INT_LITERAL, 2),
        Token(TokenType.SEMICOLON),
        Token(TokenType.CLOSE_BRACKET),
    ]


@pytest.mark.parametrize("filename", valid_programs())
def test_parse_valid_programs(filename: Path):
    """
    Test that all valid programs parse correctly
    """
    tokens = lex_file(str(filename))
    maybe_program = Program.parse(tokens)
    assert maybe_program


@pytest.mark.parametrize("filename", invalid_programs())
def test_parse_invalid_programs(filename: Path):
    """
    Test that all invalid programs don't parse
    """
    tokens = lex_file(str(filename))
    maybe_program = Program.parse(tokens)
    assert not maybe_program
