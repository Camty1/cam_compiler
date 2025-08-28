from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, Self, Type


class TerminalSymbol(Enum):
    """
    An enum containing all terminal symbols (predefined) and their regex
    """

    NUM = r"\d+\.?\d*|\.\d+"
    IDENT = r"[a-zA-Z_]+"
    PLUS = r"\+"
    MINUS = r"-"
    MULT = r"\*"
    DIV = r"/"
    POW = r"\*\*"
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
    EPSILON = r"\b\B"


class CompileItem:

    def compile(self) -> str:
        raise NotImplementedError()


class ParseItem:

    @property
    def rules(self) -> list[list[Type[Self] | TerminalSymbol]]:
        raise NotImplementedError()

    def to_compile_item(self) -> CompileItem:
        raise NotImplementedError()

@dataclass
class Start(ParseItem, CompileItem):
    """
    The first character in the parse
    """
    first: ParseItem

    @property
    def rules(self):
        return [[Sum]]

    def to_compile_item(self):
        return self

    def compile(self):
        return self.first.to_compile_item().compile()

@dataclass
class Atom(ParseItem, CompileItem):
    """
    The lowest level symbol, either a number or a channel
    """

    atom_type: Literal[TerminalSymbol.NUM] | Literal[TerminalSymbol.IDENT]
    value: str | float

    @property
    def rules(self):
        return [[TerminalSymbol.NUM], [TerminalSymbol.IDENT]]

    def to_compile_item(self):
        return self

    def compile(self):
        return str(self.value) if self.atom_type == TerminalSymbol.NUM else self.value


@dataclass
class Sum(ParseItem):
    """
    The addition or subtraction of two values.  Left associativity is forced by making recursion
    occur on the left item.
    """

    left: Self | Atom
    right: Optional[Atom]
    operator: Optional[Literal[TerminalSymbol.PLUS] | Literal[TerminalSymbol.MINUS]]

    @property
    def rules(self):
        return [
            [Self, TerminalSymbol.PLUS, Atom],
            [Self, TerminalSymbol.MINUS, Atom],
            [Atom],
        ]

    def to_compile_item(self):
        # Is an Atom
        if self.operator is None:
            return self.left

        # Is a BinaryOp
        return BinaryOp(
            self.left.to_compile_item(), self.right.to_compile_item(), self.operator
        )


@dataclass
class BinaryOp:
    """
    The compiler output of a Sum
    """

    left: Self | Atom
    right: Atom
    operator: Literal[TerminalSymbol.PLUS] | Literal[TerminalSymbol.MINUS]


def main():
    symbols: list[tuple[TerminalSymbol, Optional[str, float]]] = [
        (TerminalSymbol.NUM, 3),
        (TerminalSymbol.PLUS, None),
        (TerminalSymbol.IDENT, "x"),
        (TerminalSymbol.MINUS, None),
        (TerminalSymbol.NUM, 2.0),
    ]
