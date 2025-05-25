from parser import Program
from pathlib import Path

import pytest

from lexer import Token, TokenType, lex_file


def valid_programs(max_stage: int) -> list[Path]:
    programs: list[Path] = []
    for stage in range(1, max_stage + 1):
        programs += list(Path(f"./stage_{stage}/valid/").iterdir())

    return programs


def invalid_programs(max_stage: int) -> list[Path]:
    programs: list[Path] = []
    for stage in range(1, max_stage + 1):
        programs += list(Path(f"./stage_{stage}/valid/").iterdir())

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


@pytest.mark.parametrize("filename", valid_programs(1))
def test_parse_valid_programs(filename: Path):
    tokens = lex_file(str(filename))
    valid_program = Program.parse(tokens)
    assert valid_program


@pytest.mark.parametrize("filename", invalid_programs(1))
def test_parse_invalid_programs(filename: Path):
    tokens = lex_file(str(filename))
    valid_program = Program.parse(tokens)
    assert valid_program
