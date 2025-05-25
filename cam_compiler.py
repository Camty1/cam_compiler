#!/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12
"""
Compiles a .c file to assembly
"""

import subprocess
from sys import argv
from typing import Optional

from cam_lexer import Token, lex_file, lex_str
from cam_parser import Program


def compile_program(tokens: list[Token]) -> Optional[str]:
    """
    Parses and compiles a series of lexed tokens
    """
    program = Program.parse(tokens)
    if program:
        return program.compile()

    return None


def compile_str(input_str: str) -> Optional[str]:
    """
    Compiles an input string to its assembly string
    """
    return compile_program(lex_str(input_str))


def compile_file(filename: str) -> Optional[str]:
    """
    Compiles a file to its assembly string
    """
    return compile_program(lex_file(filename))


def main():
    """
    Compiles a program when the file is called
    """
    filename = argv[1]
    assembly_str = compile_file(filename)
    if assembly_str:
        assembly_name = filename.replace(".c", ".s")
        with open(assembly_name, "w", encoding="UTF-8") as file:
            file.write(assembly_str)

        executable_name = filename.replace(".c", "")
        subprocess.run(["gcc", assembly_name, "-o", executable_name], check=True)


if __name__ == "__main__":
    main()
