from enum import Enum


class TerminalSymbol(Enum):
    """
    An enum containing all terminal symbols (predefined) and their regex
    """

    NUM = r"\d+\.?\d*|\.\d+"
    AS = r"\bas\b"
    PI = r"\bpi\b"
    IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"
    PLUS = r"\+"
    MINUS = r"-"
    MULT = r"\*"
    DIV = r"/"
    POW = r"\*\*"
    EQUALS = r"="
    L_PAREN = r"\("
    R_PAREN = r"\)"
    L_SQUARE = r"\["
    R_SQUARE = r"\]"
    L_CURL = r"\{"
    R_CURL = r"\}"
    COLON = r":"
    SEMICOLON = r";"
    COMMA = r","
    PERIOD = r"\."
    PIPE = r"\|"
    NEWLINE = "\n"
    EPSILON = r"\b\B"
