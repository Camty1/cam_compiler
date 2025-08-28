import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from pprint import pprint
from typing import NewType, Optional, Type

from compiler_base import TerminalSymbol


@dataclass
class Trie:
    value: Optional[str | Enum]
    children: list["Trie"] = field(default_factory=list)
    visited: list[int] = field(default_factory=list)

    @property
    def num_visits(self) -> int:
        return len(self.visited)

    def populate_trie(self, symbols: list[str | Enum], rule_idx: int) -> None:
        self.visited.append(rule_idx)
        if not symbols:
            return

        for child in self.children:
            if symbols[0] == child.value:
                child.populate_trie(symbols[1:], rule_idx)
                return

        new_child = Trie(symbols[0])
        self.children.append(new_child)
        new_child.populate_trie(symbols[1:], rule_idx)

    def print(self, level=0):
        new_line = "\n"
        indent = "    " * level
        return (
            f"{indent}{str(self.value) if self.value is not None else 'root'}{self.visited}"
        ) + (
            f" ::= {' | '.join(str(child.value) for child in self.children)}"
            + new_line
            + f"{new_line.join(child.print(level+1) for child in self.children)}"
            if self.children
            else ""
        )

    def __repr__(self):
        return self.print()


@dataclass
class RadixTree:
    values: list[str | Enum]
    children: list["RadixTree"] = field(default_factory=list)
    visited: list[int] = field(default_factory=list)

    @classmethod
    def from_trie(cls, trie_root: Trie) -> "RadixTree":
        radix_root = cls([], [], trie_root.visited)

        stack: list[tuple["RadixTree", Trie]] = [(radix_root, trie_root)]
        while stack:
            radix_node, trie_node = stack.pop()
            if len(trie_node.children) == 0:
                continue

            if (
                len(trie_node.children) == 1
                and trie_node.visited == trie_node.children[0].visited
            ):
                child_node = trie_node.children[0]
                child_value = child_node.value
                assert child_value
                radix_node.values.append(child_value)
                stack.append((radix_node, child_node))
            else:
                for trie_child_node in trie_node.children:
                    value = trie_child_node.value
                    assert value
                    radix_child_node = RadixTree([value], [], trie_child_node.visited)
                    radix_node.children.append(radix_child_node)
                    stack.append((radix_child_node, trie_child_node))

        return radix_root

    def print(self, level=0):
        new_line = "\n"
        indent = "    " * level
        return (
            f"{indent}{str(self.values) if self.values else 'root'}{self.visited}"
        ) + (
            f" ::= {' | '.join(str(child.values) for child in self.children)}"
            + new_line
            + f"{new_line.join(child.print(level+1) for child in self.children)}"
            if self.children
            else ""
        )

    def __repr__(self):
        return self.print()


@dataclass
class ParseTree:
    """
    A representation of a parse tree
    """

    node_type: Enum
    value: Optional[float | str] = None
    children: list["ParseTree"] = field(default_factory=list)

    def print(self, indent: int = 0) -> str:
        return (
            "    " * indent
            + (
                f"({self.node_type.name}, {self.value})"
                if self.value
                else f"({self.node_type.name})"
            )
            + (":" if self.children else "")
            + "\n"
            + "".join([child.print(indent + 1) for child in self.children])
        )

    def __str__(self):
        return self.print()


class ParseError(Exception):
    """
    If an error was found parsing
    """


def extract_symbol(
    symbol_str: str, non_terminal_symbol_enum: Optional[Type[Enum]] = None
) -> str | Enum:
    symbol_name = re.sub(r"<|>", "", symbol_str).strip()
    try:
        terminal_symbol = getattr(TerminalSymbol, symbol_name)
        return terminal_symbol
    except AttributeError:
        if non_terminal_symbol_enum:
            try:
                non_terminal_symbol = getattr(non_terminal_symbol_enum, symbol_name)
                return non_terminal_symbol
            except AttributeError:
                raise AttributeError(
                    f"'{symbol_name} is neither a TerminalSymbol nor NonTerminalSymbol"
                )
        else:
            return symbol_name


def parse_backus_naur(
    input_str: str,
) -> tuple[
    set[Enum],
    type[Enum],
    Enum,
    dict[Enum, list[list[Enum]]],
]:
    lines = input_str.strip().splitlines()
    terminal_symbols: set[Enum] = set()
    non_terminal_name_list: list[str] = []
    for line in lines:
        new_non_terminal_str = [x.strip() for x in line.split("::=")][0]
        new_non_terminal_name = extract_symbol(new_non_terminal_str)
        assert isinstance(
            new_non_terminal_name, str
        ), f"Trying to redefine '{new_non_terminal_name}'"
        non_terminal_name_list.append(new_non_terminal_name)

    non_terminal_enum_def: dict[str, int] = {
        name: i for i, name in enumerate(non_terminal_name_list)
    }

    NonTerminalSymbol = Enum("NonTerminalSymbol", non_terminal_enum_def)

    productions: dict[Enum, list[list[Enum]]] = {}

    for line in lines:
        non_terminal_str, rules_str = (x.strip() for x in line.split("::="))
        non_terminal = extract_symbol(non_terminal_str, NonTerminalSymbol)
        assert isinstance(non_terminal, NonTerminalSymbol)
        productions[non_terminal] = []
        rules = [x.strip() for x in rules_str.split("|")]
        for rule_str in rules:
            symbol_strs = [x.strip() for x in rule_str.split()]
            symbols: list[Enum] = []
            for symbol_str in symbol_strs:
                symbol = extract_symbol(symbol_str, NonTerminalSymbol)
                assert isinstance(symbol, (TerminalSymbol, NonTerminalSymbol))
                if isinstance(symbol, TerminalSymbol):
                    terminal_symbols.add(symbol)
                symbols.append(symbol)
            productions[non_terminal].append(symbols)

    return (
        terminal_symbols,
        NonTerminalSymbol,
        NonTerminalSymbol(0),
        productions,
    )


def non_terminals_to_strings(
    productions: dict[Enum, list[list[Enum]]], non_terminal_enum: Type[Enum]
) -> tuple[dict[str, list[list[str | Enum]]], dict[str, int]]:
    non_terminal_dict: dict[str, int] = {
        non_terminal.name: non_terminal.value for non_terminal in non_terminal_enum
    }

    productions_strings: dict[str, list[list[str | Enum]]] = {}
    for non_terminal, rules in productions.items():
        new_rules: list[list[str | Enum]] = []
        for rule in rules:
            new_rule: list[str | Enum] = [
                symbol.name if symbol in non_terminal_enum else symbol
                for symbol in rule
            ]
            new_rules.append(new_rule)

        productions_strings[non_terminal.name] = new_rules

    return productions_strings, non_terminal_dict


def direct_transformation(
    non_terminal: str, rules: list[list[Enum | str]], non_terminal_dict: dict[str, int]
) -> dict[str, list[list[Enum | str]]]:
    # Create new enum
    new_non_terminal_name = non_terminal + "Prime"
    new_non_terminal_value = max(non_terminal_dict.values()) + 1
    non_terminal_dict[new_non_terminal_name] = new_non_terminal_value

    # Find recursive and non_recursive rules, converting to the new enum
    recursive_rules: list[list[Enum | str]] = []
    non_recursive_rules: list[list[Enum | str]] = []
    for rule in rules:
        recursive = False
        while rule[0] == non_terminal:
            recursive = True
            rule.pop(0)

        if recursive:
            recursive_rules.append(rule + [new_non_terminal_name])
        else:
            non_recursive_rules.append(rule + [new_non_terminal_name])

    # Create new productions if there are any recursive rules
    if recursive_rules:
        recursive_rules.append([TerminalSymbol.EPSILON])
        return {
            non_terminal: non_recursive_rules,
            new_non_terminal_name: recursive_rules,
        }
    non_terminal_dict.pop(new_non_terminal_name)
    return {non_terminal: rules}


def make_right_recursive_str(
    productions: dict[str, list[list[str | Enum]]], non_terminal_dict: dict[str, int]
) -> None:

    old_non_terminals = list(productions.keys())
    num_non_terminals = len(old_non_terminals)
    for i in range(num_non_terminals):
        non_terminal_i = old_non_terminals[i]
        for j in range(i):
            non_terminal_j = old_non_terminals[j]
            new_rules: list[list[Enum | str]] = []
            for rule in productions[non_terminal_i]:
                if rule[0] == non_terminal_j:
                    new_rules.extend(
                        [
                            production_rule + rule[1:]
                            for production_rule in productions[non_terminal_j]
                        ]
                    )
                else:
                    new_rules.append(rule)
            productions[non_terminal_i] = new_rules

        direct_productions = direct_transformation(
            non_terminal_i, productions[non_terminal_i], non_terminal_dict
        )
        productions |= direct_productions


def strings_to_non_terminals(
    productions_strings: dict[str, list[list[str | Enum]]],
    non_terminal_dict: dict[str, int],
) -> tuple[dict[Enum, list[list[Enum]]], Type[Enum]]:

    non_terminal_enum = Enum("NonTerminalSymbol", non_terminal_dict)
    productions = {
        getattr(non_terminal_enum, production_key): [
            [
                (
                    getattr(non_terminal_enum, symbol)
                    if isinstance(symbol, str)
                    else symbol
                )
                for symbol in rule
            ]
            for rule in production_rules
        ]
        for production_key, production_rules in productions_strings.items()
    }

    return productions, non_terminal_enum


def make_right_recursive(
    productions: dict[Enum, list[list[Enum]]], non_terminal_enum: Type[Enum]
) -> tuple[dict[Enum, list[list[Enum]]], Type[Enum]]:

    productions_strings, non_terminal_dict = non_terminals_to_strings(
        productions, non_terminal_enum
    )

    make_right_recursive_str(productions_strings, non_terminal_dict)

    new_productions, new_non_terminal_enum = strings_to_non_terminals(
        productions_strings, non_terminal_dict
    )

    return new_productions, new_non_terminal_enum


def get_common_prefix(
    rules: list[list[str | Enum]],
) -> tuple[list[str | Enum], list[int]]:
    trie_root = Trie(None)
    for idx, rule in enumerate(rules):
        trie_root.populate_trie(rule, idx)

    radix_root = RadixTree.from_trie(trie_root)
    if radix_root.values and len(radix_root.visited) > 1:
        return radix_root.values, radix_root.visited

    for child in radix_root.children:
        if len(child.visited) > 1:
            return child.values, child.visited

    return [], []


def left_factor_str(
    productions: dict[str, list[list[str | Enum]]], non_terminal_dict: dict[str, int]
) -> None:

    non_terminal_stack = list(productions.keys())
    num_common_prefixes = [0] * len(productions.keys())

    while non_terminal_stack:
        non_terminal = non_terminal_stack.pop()
        common_prefix, rule_indices = get_common_prefix(productions[non_terminal])

        if common_prefix and rule_indices:
            non_terminal_idx = non_terminal_dict[non_terminal]
            new_non_terminal = (
                non_terminal + f"Follower{num_common_prefixes[non_terminal_idx]}"
            )

            num_common_prefixes[non_terminal_idx] += 1
            non_terminal_dict[new_non_terminal] = max(non_terminal_dict.values()) + 1
            num_common_prefixes.append(0)

            sorted_rule_indices = sorted(rule_indices, reverse=True)
            new_rules: list[list[str | Enum]] = []
            for index in sorted_rule_indices:
                old_rule = productions[non_terminal].pop(index)
                assert old_rule[: len(common_prefix)] == common_prefix
                new_rule = old_rule[len(common_prefix) :]
                # Check if it is empty
                if not new_rule:
                    new_rule.append(TerminalSymbol.EPSILON)
                new_rules.append(new_rule)

            productions[non_terminal].append(common_prefix + [new_non_terminal])
            productions[new_non_terminal] = new_rules

            non_terminal_stack.append(non_terminal)
            non_terminal_stack.append(new_non_terminal)


def lex(
    input_str: str, terminal_symbols: set[Enum]
) -> list[tuple[Enum, Optional[float | str]]]:
    re_string = r"|".join([symbol.value for symbol in terminal_symbols])
    raw_symbols = re.findall(re_string, input_str)
    symbols: list[tuple[Enum, Optional[float | str]]] = []
    for raw_symbol in raw_symbols:
        for terminal_symbol in terminal_symbols:
            if re.match(terminal_symbol.value, raw_symbol):
                value = None
                if terminal_symbol == TerminalSymbol.NUM:
                    value = float(raw_symbol)
                elif terminal_symbol == TerminalSymbol.IDENT:
                    value = raw_symbol

                symbols.append((terminal_symbol, value))

    return symbols


def parse_symbols(
    symbols: list[tuple[Enum, Optional[float | str]]],
    productions: dict[Enum, list[list[Enum]]],
    starting_symbol: Enum,
    non_terminal_enum: Type[Enum],
) -> ParseTree:
    root = ParseTree(starting_symbol)
    node_queue = [root]
    symbol_index = 0

    while node_queue:
        current_node = node_queue.pop(0)
        if symbol_index < len(symbols):
            current_symbol_type, current_symbol_value = symbols[symbol_index]

            # At a terminal node in the Parse Tree
            if current_node.node_type in TerminalSymbol:

                # Current symbol matches expected type in the parse tree
                if current_node.node_type == current_symbol_type:
                    current_node.value = current_symbol_value
                    symbol_index += 1
                    continue

                # Does not match
                raise ParseError(
                    f"Current symbol is '{current_symbol_type.name}' with value '{current_symbol_value}', expected '{current_node.node_type.name}'."
                )

            # Expand the tree
            epsilon_rule = -1
            matching_rule = -1
            non_terminal_rule = -1
            for idx, rule in enumerate(productions[current_node.node_type]):
                if rule[0] == TerminalSymbol.EPSILON:
                    epsilon_rule = idx

                if rule[0] == current_symbol_type:
                    matching_rule = idx

                if isinstance(rule[0], non_terminal_enum):
                    if non_terminal_rule != -1:
                        raise ParseError(
                            "Multiple Non-Terminal rules for a given production, grammar is not backtrack free"
                        )
                    non_terminal_rule = idx

            if matching_rule != -1:
                new_nodes = [
                    ParseTree(rule_symbol)
                    for rule_symbol in productions[current_node.node_type][
                        matching_rule
                    ]
                ]
                current_node.children = new_nodes
                node_queue = new_nodes + node_queue
                continue

            if epsilon_rule != -1:
                current_node.children = [ParseTree(TerminalSymbol.EPSILON)]
                continue

            if non_terminal_rule != -1:
                new_nodes = [
                    ParseTree(rule_symbol)
                    for rule_symbol in productions[current_node.node_type][
                        non_terminal_rule
                    ]
                ]
                current_node.children = new_nodes
                node_queue = new_nodes + node_queue
                continue

        else:
            epsilon_rule = -1
            non_terminal_rule = -1

            for idx, rule in enumerate(productions[current_node.node_type]):
                if rule[0] == TerminalSymbol.EPSILON:
                    epsilon_rule = idx

                if isinstance(rule[0], non_terminal_enum):
                    if non_terminal_rule != -1:
                        raise ParseError(
                            "Multiple Non-Terminal rules for a given production, grammar is not backtrack free"
                        )
                    non_terminal_rule = idx

            if epsilon_rule != -1:
                current_node.children = [ParseTree(TerminalSymbol.EPSILON)]
                continue

            if non_terminal_rule != -1:
                new_nodes = [
                    ParseTree(rule_symbol)
                    for rule_symbol in productions[current_node.node_type][
                        non_terminal_rule
                    ]
                ]
                current_node.children = new_nodes
                node_queue = new_nodes + node_queue
                continue

        raise ParseError("No matching symbol, epsilon, or non terminal.  Panic!!!")

    return root


def main():

    math_backus_naur = """
        <Expr>     ::= <Expr> <PLUS> <Term> | <Expr> <MINUS> <Term> | <Term>
        <Term>     ::= <Term> <MULT> <Factor> | <Term> <DIV> <Factor> | <Factor>
        <Factor>   ::= <L_PAREN> <Expr> <R_PAREN> | <NUM> | <IDENT>
    """
    math_backus_naur_complex = """
        <Expr>      ::= <Expr> <PLUS> <Term> | <Expr> <MINUS> <Term> | <Term>
        <Term>      ::= <Term> <MULT> <Factor> | <Term> <DIV> <Factor> | <Factor>
        <Factor>    ::= <L_PAREN> <Expr> <R_PAREN> | <NUM> | <IDENT> | <IDENT> <L_PAREN> <ExprList> <R_PAREN> | <IDENT> <L_SQUARE> <ExprList> <R_SQUARE>
        <ExprList>  ::= <Expr> <COMMA> <ExprList> | <Expr>
    """

    left_factor_backus_naur = """
        <Factor>   ::= <L_PAREN> <Expr> <R_PAREN> | <NUM> | <IDENT> | <IDENT> <L_PAREN> <ExprList> <R_PAREN> | <IDENT> <L_SQUARE> <ExprList> <R_SQUARE>
        <Expr>     ::= <PLUS> | <MINUS>
        <ExprList> ::= <Expr> <COMMA> <ExprList> | <Expr>
    """

    fee_backus_naur = """<Fee> ::= <Fee> <PLUS> | <MINUS>"""

    terminal_symbols, non_terminal_enum, starting_symbol, productions = (
        parse_backus_naur(math_backus_naur)
    )

    productions_str, non_terminal_dict = non_terminals_to_strings(
        productions, non_terminal_enum
    )
    make_right_recursive_str(productions_str, non_terminal_dict)
    left_factor_str(productions_str, non_terminal_dict)

    productions, non_terminal_enum = strings_to_non_terminals(
        productions_str, non_terminal_dict
    )

    test_expression = "3 * (x - y) + z / 2.0"

    symbols = lex(test_expression, terminal_symbols)

    pprint(symbols)

    parse_tree = parse_symbols(
        symbols, productions, non_terminal_enum.Expr, non_terminal_enum
    )

    print(parse_tree)


if __name__ == "__main__":
    main()
