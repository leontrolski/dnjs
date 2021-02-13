from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Iterator,
    Tuple,
    Union,
)

from dnjs.tokeniser_2 import Token, TokenStream, eof, newline


class ParseError(Exception):
    pass


def raise_null_error(token_stream: TokenStream, _: int) -> Node:
    raise ParseError("%s can't be used in prefix position" % token_stream.current)


def raise_left_error(token_stream: TokenStream, _: int, __: Node) -> Node:
    # Hm is this not called because of binding power?
    raise ParseError("%s can't be used in infix position" % token_stream.current)


@dataclass
class Node:
    token: Token
    children: List[Node]

    def __repr__(self) -> str:
        if not self.children:
            return str(self.token.value)
        args = ",".join([" " + repr(c) for c in self.children])
        return f'["{self.token.type}" {args}]'


Nud = Callable[[TokenStream, int], Node]
Led = Callable[[TokenStream, int, Node], Node]


@dataclass
class RuleMap:
    """Register some rules, comes with two decorators:

        @rule_map.register_null(-1, ["name", "number"])
        @rule_map.register_left(5, ["?"], is_left_right_assoc=True)

    These populate the maps .null and .left

    """
    # where str is a token.type
    null: Dict[str, Tuple[Nud, int]] = field(default_factory=dict)
    left: Dict[str, Tuple[Led, int, int]] = field(default_factory=dict)

    def register_null(
        self,
        bp: int,
        token_types: List[str],
    ) -> Callable[[Nud], Nud]:
        def inner(f: Nud) -> Nud:
            for token_type in token_types:
                self.null[token_type] = f, bp
                if token_type not in self.left:
                    self.left[token_type] = raise_left_error, 0, 0
            return f

        return inner

    def register_left(
        self,
        bp: int,
        token_types: List[str],
        is_left_right_assoc: bool = False,
    ) -> Callable[[Led], Led]:
        def inner_nud(f: Led) -> Led:
            lbp = bp
            rbp = bp - 1 if is_left_right_assoc else bp
            for token_type in token_types:
                self.left[token_type] = f, lbp, rbp
                if token_type not in self.null:
                    self.null[token_type] = raise_null_error, 0
            return f

        return inner_nud


def eat(token_stream: TokenStream, token_type: str) -> None:
    """Assert the value of the current token, then move to the next token."""
    if token_type and not token_stream.current.type == token_type:
        raise ParseError("expected %s, got %s" % (token_type, token_stream.current))
    next(token_stream)


def parse(rule_map: RuleMap, token_stream: TokenStream, rbp: int = 0) -> Node:
    """
    parse to the right, eating tokens until we encounter a token with binding
    power LESS THAN OR EQUAL TO rbp.
    """
    if token_stream.current.type == eof:
        raise ParseError("Unexpected end of input")
    if token_stream.current.type not in rule_map.null:
        raise ParseError("Unexpected token %r" % token_stream.current)

    nud, _bp = rule_map.null[token_stream.current.type]
    node = nud(token_stream, _bp)

    while True:
        if token_stream.current.type not in rule_map.left:
            raise ParseError("Unexpected token %r" % token_stream.current)

        led, _lbp, _rbp = rule_map.left[token_stream.current.type]
        # Examples:
        # If we see 1*2+  , rbp = 27 and lbp = 25, so stop.
        # If we see 1+2+  , rbp = 25 and lbp = 25, so stop.
        # If we see 1**2**, rbp = 26 and lbp = 27, so keep going.
        if rbp >= _lbp:
            break
        node = led(token_stream, _rbp, node)

    return node
