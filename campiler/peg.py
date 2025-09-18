"""
Implements a Parsing Expression Grammar (PEG) following Guido's Medium articles
"""

import re
from dataclasses import dataclass
from enum import Enum
from pprint import pprint
from typing import Any, Callable, Optional, Self

from compiler_base import TerminalSymbol


@dataclass
class Token:
    """
    A TerminalSymbol and the parsed string corresponding to the TerminalSymbol.
    """

    type: TerminalSymbol
    value: str


class Tokenizer:
    """
    Parses an input string into tokens, and then provides an interface for viewing/ accessing the
    tokens.
    """

    def __init__(self, input_str: str):
        self._tokens = self._parse_tokens(input_str)
        self._pos = 0

    def _parse_tokens(self, input_str: str) -> list[Token]:
        re_str = r"|".join([symbol.value for symbol in TerminalSymbol])
        matches = re.findall(re_str, input_str)

        tokens: list[Token] = []
        for match in matches:
            for symbol in TerminalSymbol:
                if re.match(symbol.value, match):
                    tokens.append(Token(symbol, match))
                    break

        tokens.append(Token(TerminalSymbol.EPSILON, ""))
        return tokens

    def mark(self) -> int:
        """
        Get the position of the current token.
        """
        return self._pos

    def reset(self, pos: int):
        """
        Reset to a previous token.
        """
        self._pos = pos

    def peek_token(self) -> Token:
        """
        Look at the next token, but don't change positions.
        """
        return self._tokens[self._pos]

    def get_token(self) -> Token:
        """
        Look at the next token, and move forward.
        """
        token = self.peek_token()
        self._pos += 1
        return token


class NodeType(Enum):
    """
    AST node types
    """

    STATEMENT = 0
    HIDDEN_ASSIGNMENT = 1
    ASSIGNMENT = 2
    LABELED_CHANNEL = 3
    STANDALONE_CHANNEL = 4
    LABEL = 5
    EXPRESSION = 6
    ADD = 7
    SUB = 8
    TERM = 9
    MULT = 10
    DIV = 11
    FACTOR = 12
    FUNCTION = 13
    PAREN_EXPRESSION = 14
    ARGUMENTS = 15


@dataclass
class Node:
    """
    Populates the AST
    """

    type: NodeType
    children: list[Self | Token]


class Parser:
    """
    Parses tokens into an AST
    """

    def __init__(
        self, *, tokenizer: Optional[Tokenizer] = None, input_str: Optional[str] = ""
    ):
        if tokenizer:
            self._tokenizer = tokenizer
        elif input_str:
            self._tokenizer = Tokenizer(input_str)
        else:
            raise ValueError("Need to pass either a tokenizer or an input string")

        self.memo: dict[
            tuple[int, Callable, tuple[Any, ...]], tuple[Optional[Node], int]
        ] = {}

    def mark(self) -> int:
        """
        Get the position of the current token.
        """
        return self._tokenizer.mark()

    def reset(self, pos: int):
        """
        Reset to a previous position.
        """
        return self._tokenizer.reset(pos)

    def expect(self, arg: TerminalSymbol) -> Optional[Token]:
        """
        If the current token matches the expected type, then return it, otherwise return None.
        """
        token = self._tokenizer.peek_token()
        if token.type == arg:
            return self._tokenizer.get_token()

        return None

    def parse(self) -> Optional[Token]:
        """
        Parse tokens into an AST.  Must be overridden by the inheriting class
        """
        raise NotImplementedError()


def memoize(func: Callable) -> Callable:
    """
    A memoization decorator
    """

    def memoize_wrapper(self: Parser, *args: tuple[Any, ...]) -> Optional[Node]:
        pos = self.mark()
        key = (pos, func, args)
        if key in self.memo:
            result, end_pos = self.memo[key]
            self.reset(end_pos)

        else:
            result = func(self, *args)
            end_pos = self.mark()
            self.memo[key] = (result, end_pos)

        return result

    return memoize_wrapper


def left_recursive_memoize(func: Callable) -> Callable:
    """
    A memoization decorator for left recursive definitions
    """

    def left_recursive_memoize_wrapper(
        self: Parser, *args: tuple[Any, ...]
    ) -> Optional[Node]:
        pos = self.mark()
        key = (pos, func, args)
        if key in self.memo:
            result, end_pos = self.memo[key]
            self.reset(end_pos)

        else:
            last_result, last_pos = (None, pos)
            self.memo[key] = (last_result, last_pos)

            while True:
                self.reset(pos)
                result = func(self, *args)
                end_pos = self.mark()
                if end_pos <= last_pos:
                    break

                last_result, last_pos = (result, end_pos)
                self.memo[key] = (result, end_pos)

            result = last_result
            self.reset(last_pos)

        return result

    return left_recursive_memoize_wrapper


class RightRecursiveToyParser(Parser):

    @memoize
    def expr(self) -> Optional[Node | Token]:
        if a := self.atom():
            pos = self.mark()
            if self.expect(TerminalSymbol.PLUS):
                if e := self.expr():
                    return Node(NodeType.ADD, [a, e])

            self.reset(pos)
            if self.expect(TerminalSymbol.MINUS):
                if e := self.expr():
                    return Node(NodeType.SUB, [a, e])

            self.reset(pos)

            return a

        return None

    @memoize
    def atom(self) -> Optional[Token]:
        if tok := self.expect(TerminalSymbol.NUM):
            return tok

        if tok := self.expect(TerminalSymbol.IDENT):
            return tok

        return None

    def parse(self):
        return self.expr()


class RightRecursiveYamlPlotParser(Parser):

    def statement(self) -> Optional[Node | Token]:
        pos = self.mark()
        if assignment := self.assignment():
            if self.expect(TerminalSymbol.EPSILON):
                return assignment
            self.reset(pos)

        if standalone_channel := self.standalone_channel():
            if self.expect(TerminalSymbol.EPSILON):
                return standalone_channel
            self.reset(pos)

        return None

    def assignment(self) -> Optional[Node]:
        pos = self.mark()
        if channel := self.expect(TerminalSymbol.IDENT):
            if self.expect(TerminalSymbol.EQUALS):
                if expr := self.expression():
                    if self.expect(TerminalSymbol.SEMICOLON):
                        return Node(NodeType.HIDDEN_ASSIGNMENT, [channel, expr])

                    return Node(NodeType.ASSIGNMENT, [channel, expr])

        self.reset(pos)
        return None

    def standalone_channel(self) -> Optional[Node | Token]:
        if channel := self.expect(TerminalSymbol.IDENT):
            if label := self.label():
                return Node(NodeType.LABELED_CHANNEL, [channel, label])

            return channel

        return None

    def label(self) -> Optional[Token]:
        pos = self.mark()
        if self.expect(TerminalSymbol.AS):
            if channel := self.expect(TerminalSymbol.IDENT):
                return channel
            self.reset(pos)

        return None

    def expression(self) -> Optional[Node | Token]:
        pos = self.mark()
        if term := self.term():
            if self.expect(TerminalSymbol.PLUS):
                if factor := self.factor():
                    return Node(NodeType.ADD, [term, factor])
                self.reset(pos)
                return None

            if self.expect(TerminalSymbol.MINUS):
                if factor := self.factor():
                    return Node(NodeType.SUB, [term, factor])
                self.reset(pos)
                return None

            return term

        return None

    def term(self) -> Optional[Node | Token]:
        pos = self.mark()
        if factor := self.factor():
            if self.expect(TerminalSymbol.MULT):
                if second_factor := self.factor():
                    return Node(NodeType.MULT, [factor, second_factor])

                self.reset(pos)
                return None

            if self.expect(TerminalSymbol.DIV):
                if second_factor := self.factor():
                    return Node(NodeType.DIV, [factor, second_factor])

                self.reset(pos)
                return None

            return factor

        return None

    def factor(self) -> Optional[Node | Token]:
        if function := self.function():
            return function

        pos = self.mark()
        if self.expect(TerminalSymbol.L_PAREN):
            if expression := self.expression():
                if self.expect(TerminalSymbol.R_PAREN):
                    return Node(NodeType.PAREN_EXPRESSION, [expression])
            self.reset(pos)
            return None

        if pi := self.expect(TerminalSymbol.PI):
            return pi

        if channel := self.expect(TerminalSymbol.IDENT):
            return channel

        if num := self.expect(TerminalSymbol.NUM):
            return num

        return None

    def function(self) -> Optional[Node]:
        pos = self.mark()
        if name := self.expect(TerminalSymbol.IDENT):
            name_and_args: list[Token | Node] = [name]
            if self.expect(TerminalSymbol.L_PAREN):
                if expression := self.expression():
                    expressions = [expression]

                    while self.expect(TerminalSymbol.COMMA) and (
                        expresion := self.expression()
                    ):
                        expressions.append(expresion)

                    name_and_args += expressions
                    if self.expect(TerminalSymbol.R_PAREN):
                        return Node(NodeType.FUNCTION, name_and_args)

                    self.reset(pos)
                    return None

                if self.expect(TerminalSymbol.R_PAREN):
                    return Node(NodeType.FUNCTION, name_and_args)

        self.reset(pos)
        return None


class YamlPlotParser(Parser):

    @memoize
    def statement(self) -> Optional[Node]:
        pos = self.mark()
        if (hidden_assignment := self.hidden_assignment()) and self.expect(
            TerminalSymbol.EPSILON
        ):
            return Node(NodeType.STATEMENT, [hidden_assignment])

        self.reset(pos)

        if (assignment := self.assignment()) and self.expect(TerminalSymbol.EPSILON):
            return Node(NodeType.STATEMENT, [assignment])

        self.reset(pos)

        if (labeled_channel := self.labeled_channel()) and self.expect(
            TerminalSymbol.EPSILON
        ):
            return Node(NodeType.STATEMENT, [labeled_channel])

        self.reset(pos)

        if (standalone_channel := self.standalone_channel()) and self.expect(
            TerminalSymbol.EPSILON
        ):
            return Node(NodeType.STATEMENT, [standalone_channel])

        self.reset(pos)

        return None

    @memoize
    def hidden_assignment(self) -> Optional[Node]:
        pos = self.mark()
        if (assignment := self.assignment()) and self.expect(TerminalSymbol.SEMICOLON):
            return Node(NodeType.HIDDEN_ASSIGNMENT, [assignment])

        self.reset(pos)

        return None

    @memoize
    def assignment(self) -> Optional[Node]:
        pos = self.mark()
        if (
            (ident := self.expect(TerminalSymbol.IDENT))
            and (self.expect(TerminalSymbol.EQUALS))
            and (expression := self.expression())
        ):
            if self.expect(TerminalSymbol.SEMICOLON):
                return Node(NodeType.HIDDEN_ASSIGNMENT, [ident, expression])

            return Node(NodeType.ASSIGNMENT, [ident, expression])

        self.reset(pos)

        return None

    @memoize
    def labeled_channel(self) -> Optional[Node]:
        pos = self.mark()
        if (standalone_channel := self.standalone_channel()) and (
            label := self.label()
        ):
            return Node(NodeType.LABELED_CHANNEL, [standalone_channel, label])

        self.reset(pos)

        return None

    @memoize
    def standalone_channel(self) -> Optional[Node]:
        pos = self.mark()
        if ident := self.expect(TerminalSymbol.IDENT):
            if label := self.label():
                return Node(NodeType.LABELED_CHANNEL, [ident, label])

            return Node(NodeType.STANDALONE_CHANNEL, [ident])

        self.reset(pos)

        return None

    @memoize
    def label(self) -> Optional[Node]:
        pos = self.mark()
        if (self.expect(TerminalSymbol.AS)) and (
            ident := self.expect(TerminalSymbol.IDENT)
        ):
            return Node(NodeType.LABEL, [ident])

        self.reset(pos)

        return None

    @left_recursive_memoize
    def expression(self) -> Optional[Node]:
        pos = self.mark()
        if expression := self.expression():
            expression_pos = self.mark()
            if (plus := self.expect(TerminalSymbol.PLUS)) and (term := self.term()):
                return Node(NodeType.EXPRESSION, [expression, plus, term])

            self.reset(expression_pos)

            if (minus := self.expect(TerminalSymbol.MINUS)) and (term := self.term()):
                return Node(NodeType.EXPRESSION, [expression, minus, term])

            self.reset(expression_pos)

        self.reset(pos)

        if term := self.term():
            return Node(NodeType.EXPRESSION, [term])

        self.reset(pos)

        return None

    @left_recursive_memoize
    def add(self) -> Optional[Node]:
        pos = self.mark()
        if (
            (expression := self.expression())
            and (self.expect(TerminalSymbol.PLUS))
            and (term := self.term())
        ):
            return Node(NodeType.ADD, [expression, term])

        self.reset(pos)

        return None

    @left_recursive_memoize
    def sub(self) -> Optional[Node]:
        pos = self.mark()
        if (
            (expression := self.expression())
            and (self.expect(TerminalSymbol.MINUS))
            and (term := self.term())
        ):
            return Node(NodeType.SUB, [expression, term])

        self.reset(pos)

        return None

    @left_recursive_memoize
    def term(self) -> Optional[Node]:
        pos = self.mark()
        if term := self.term():
            term_pos = self.mark()
            if (mult := self.expect(TerminalSymbol.MULT)) and (factor := self.factor()):
                return Node(NodeType.TERM, [term, mult, factor])

            self.reset(term_pos)

            if (div := self.expect(TerminalSymbol.DIV)) and (factor := self.factor()):
                return Node(NodeType.TERM, [term, div, factor])

            self.reset(term_pos)

        self.reset(pos)

        if factor := self.factor():
            return Node(NodeType.TERM, [factor])

        self.reset(pos)

        return None

    @left_recursive_memoize
    def mult(self) -> Optional[Node]:
        pos = self.mark()
        if (
            (term := self.term())
            and (self.expect(TerminalSymbol.MULT))
            and (factor := self.factor())
        ):
            return Node(NodeType.MULT, [term, factor])

        self.reset(pos)

        return None

    @left_recursive_memoize
    def div(self) -> Optional[Node]:
        pos = self.mark()
        if (
            (term := self.term())
            and (self.expect(TerminalSymbol.DIV))
            and (factor := self.factor())
        ):
            return Node(NodeType.DIV, [term, factor])

        self.reset(pos)

        return None

    @memoize
    def factor(self) -> Optional[Node]:
        pos = self.mark()
        if function := self.function():
            return Node(NodeType.FACTOR, [function])

        self.reset(pos)

        if paren_expression := self.paren_expression():
            return Node(NodeType.FACTOR, [paren_expression])

        self.reset(pos)

        if pi := self.expect(TerminalSymbol.PI):
            return Node(NodeType.FACTOR, [pi])

        self.reset(pos)

        if ident := self.expect(TerminalSymbol.IDENT):
            return Node(NodeType.FACTOR, [ident])

        self.reset(pos)

        if num := self.expect(TerminalSymbol.NUM):
            return Node(NodeType.FACTOR, [num])

        self.reset(pos)

        return None

    @memoize
    def function(self) -> Optional[Node]:
        pos = self.mark()
        if (ident := self.expect(TerminalSymbol.IDENT)) and (
            self.expect(TerminalSymbol.L_PAREN)
        ):

            expr_pos = self.mark()

            arguments: list[Node] = []
            if expression := self.expression():
                arguments.append(expression)

                while self.expect(TerminalSymbol.COMMA) and (
                    expression := self.expression()
                ):
                    expr_pos = self.mark()
                    arguments.append(expression)

            self.reset(expr_pos)

            if self.expect(TerminalSymbol.R_PAREN):
                return Node(NodeType.FUNCTION, [ident] + arguments)

        self.reset(pos)

        return None

    @memoize
    def paren_expression(self) -> Optional[Node]:
        pos = self.mark()
        if (
            (self.expect(TerminalSymbol.L_PAREN))
            and (expression := self.expression())
            and (self.expect(TerminalSymbol.R_PAREN))
        ):
            return Node(NodeType.PAREN_EXPRESSION, [expression])

        self.reset(pos)

        return None

    def parse(self):
        return self.statement()


class SimplifiedYamlPlotParser(Parser):

    @memoize
    def statement(self) -> Optional[Node | Token]:
        pos = self.mark()
        if (hidden_assignment := self.hidden_assignment()) and self.expect(
            TerminalSymbol.EPSILON
        ):
            return hidden_assignment

        self.reset(pos)

        if (assignment := self.assignment()) and self.expect(TerminalSymbol.EPSILON):
            return assignment

        self.reset(pos)

        if (labeled_channel := self.labeled_channel()) and self.expect(
            TerminalSymbol.EPSILON
        ):
            return labeled_channel

        self.reset(pos)

        if (standalone_channel := self.standalone_channel()) and self.expect(
            TerminalSymbol.EPSILON
        ):
            return standalone_channel

        self.reset(pos)

        return None

    @memoize
    def hidden_assignment(self) -> Optional[Node | Token]:
        pos = self.mark()
        if (assignment := self.assignment()) and self.expect(TerminalSymbol.SEMICOLON):
            return Node(NodeType.HIDDEN_ASSIGNMENT, [assignment])

        self.reset(pos)

        return None

    @memoize
    def assignment(self) -> Optional[Node | Token]:
        pos = self.mark()
        if (
            (ident := self.expect(TerminalSymbol.IDENT))
            and (self.expect(TerminalSymbol.EQUALS))
            and (expression := self.expression())
        ):
            return Node(NodeType.ASSIGNMENT, [ident, expression])

        self.reset(pos)

        return None

    @memoize
    def labeled_channel(self) -> Optional[Node | Token]:
        pos = self.mark()
        if (standalone_channel := self.standalone_channel()) and (
            label := self.label()
        ):
            return Node(NodeType.LABELED_CHANNEL, [standalone_channel, label])

        self.reset(pos)

        return None

    @memoize
    def standalone_channel(self) -> Optional[Node | Token]:
        pos = self.mark()
        if ident := self.expect(TerminalSymbol.IDENT):

            return ident

        self.reset(pos)

        return None

    @memoize
    def label(self) -> Optional[Node | Token]:
        pos = self.mark()
        if (self.expect(TerminalSymbol.AS)) and (
            ident := self.expect(TerminalSymbol.IDENT)
        ):
            return ident

        self.reset(pos)

        return None

    @left_recursive_memoize
    def expression(self) -> Optional[Node | Token]:
        pos = self.mark()
        if expression := self.expression():
            expression_pos = self.mark()
            if (self.expect(TerminalSymbol.PLUS)) and (term := self.term()):
                return Node(NodeType.ADD, [expression, term])

            self.reset(expression_pos)

            if (self.expect(TerminalSymbol.MINUS)) and (term := self.term()):
                return Node(NodeType.SUB, [expression, term])

            self.reset(expression_pos)

        self.reset(pos)

        if term := self.term():
            return term

        self.reset(pos)

        return None

    @left_recursive_memoize
    def term(self) -> Optional[Node | Token]:
        pos = self.mark()
        if term := self.term():
            term_pos = self.mark()
            if (self.expect(TerminalSymbol.MULT)) and (factor := self.factor()):
                return Node(NodeType.MULT, [term, factor])

            self.reset(term_pos)

            if (self.expect(TerminalSymbol.DIV)) and (factor := self.factor()):
                return Node(NodeType.DIV, [term, factor])

            self.reset(term_pos)

        self.reset(pos)

        if factor := self.factor():
            return factor

        self.reset(pos)

        return None

    @memoize
    def factor(self) -> Optional[Node | Token]:
        pos = self.mark()
        if function := self.function():
            return function

        self.reset(pos)

        if paren_expression := self.paren_expression():
            return paren_expression

        self.reset(pos)

        if pi := self.expect(TerminalSymbol.PI):
            return pi

        self.reset(pos)

        if ident := self.expect(TerminalSymbol.IDENT):
            return ident

        self.reset(pos)

        if num := self.expect(TerminalSymbol.NUM):
            return num

        self.reset(pos)

        return None

    @memoize
    def function(self) -> Optional[Node | Token]:
        pos = self.mark()
        if (ident := self.expect(TerminalSymbol.IDENT)) and (
            self.expect(TerminalSymbol.L_PAREN)
        ):

            expr_pos = self.mark()

            arguments: list[Node] = []
            if expression := self.expression():
                arguments.append(expression)

                while self.expect(TerminalSymbol.COMMA) and (
                    expression := self.expression()
                ):
                    expr_pos = self.mark()
                    arguments.append(expression)

            self.reset(expr_pos)

            if self.expect(TerminalSymbol.R_PAREN):
                return Node(NodeType.FUNCTION, [ident] + arguments)

        self.reset(pos)

        return None

    @memoize
    def paren_expression(self) -> Optional[Node | Token]:
        pos = self.mark()
        if (
            (self.expect(TerminalSymbol.L_PAREN))
            and (expression := self.expression())
            and (self.expect(TerminalSymbol.R_PAREN))
        ):
            return Node(NodeType.PAREN_EXPRESSION, [expression])

        self.reset(pos)

        return None

    def parse(self):
        return self.statement()


def campile(
    root: Node, vars: dict[str, float], functions: dict[str, Callable]
) -> list[str]:
    """
    Takes a parse tree, uses it to update the variables in vars, and returns a list of channels to display
    """

    display_channel_names: list[str] = []

    def compile_helper(node_or_token: Node | Token):
        if isinstance(node_or_token, Token):
            token = node_or_token
            if token.type == TerminalSymbol.NUM:
                return float(token.value)
            if token.type == TerminalSymbol.IDENT:
                return vars[token.value]
            return None

        node = node_or_token
        if node.type in [NodeType.ASSIGNMENT, NodeType.HIDDEN_ASSIGNMENT]:
            assert isinstance(node.children[0], Token)
            channel_name = node.children[0].value
            value = compile_helper(node.children[1])
            vars[channel_name] = value
            if node.type == NodeType.ASSIGNMENT:
                display_channel_names.append(channel_name)
            return None

        if node.type == NodeType.STANDALONE_CHANNEL:
            assert isinstance(node.children[0], Token)
            channel_name = node.children[0].value
            display_channel_names.append(channel_name)
            return None

        if node.type == NodeType.LABELED_CHANNEL:
            assert isinstance(node.children[0], Token)
            channel_name = node.children[0].value
            assert isinstance(node.children[1], Token)
            channel_label = node.children[1].value
            display_channel_names.append(channel_name + " as " + channel_label)
            return None

        if node.type == NodeType.ADD:
            x = compile_helper(node.children[0])
            y = compile_helper(node.children[1])
            return x + y

        if node.type == NodeType.SUB:
            x = compile_helper(node.children[0])
            y = compile_helper(node.children[1])
            return x - y

        if node.type == NodeType.MULT:
            x = compile_helper(node.children[0])
            y = compile_helper(node.children[1])
            return x * y

        if node.type == NodeType.DIV:
            x = compile_helper(node.children[0])
            y = compile_helper(node.children[1])
            return x / y

        if node.type == NodeType.PAREN_EXPRESSION:
            return compile_helper(node.children[0])

        if node.type == NodeType.FUNCTION:
            assert isinstance(node.children[0], Token)
            function_name = node.children[0].value
            arguments = [compile_helper(child) for child in node.children[1:]]
            return functions[function_name](*arguments)

        return None

    compile_helper(root)

    return display_channel_names


def main():
    vars = {"x": 1, "shoop": 2}
    functions = {"max": max}

    breakpoint()

    tokenizer = Tokenizer("hello = 3 - x + max(3 * 2, shoop + (1 + 2))")
    parser = SimplifiedYamlPlotParser(tokenizer=tokenizer)
    bongo = parser.parse()
    channels = campile(bongo, vars, functions)

    tokenizer = Tokenizer("boop = 3 - x + max(3 / 2, (1 + 2))")
    parser = SimplifiedYamlPlotParser(tokenizer=tokenizer)
    bongo = parser.parse()
    channels += campile(bongo, vars, functions)

    tokenizer = Tokenizer("beep as scoop")
    parser = SimplifiedYamlPlotParser(tokenizer=tokenizer)
    bongo = parser.parse()
    channels += campile(bongo, vars, functions)

    print(channels)


if __name__ == "__main__":
    main()
