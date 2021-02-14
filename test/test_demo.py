from dataclasses import dataclass
from typing import Any, List

import dnjs.tokeniser as t


@dataclass
class Node:
    token: t.Token
    children: List["Node"]
    is_quoted: bool = False

    def __str__(self) -> str:
        if self.token.type in t.atoms:
            s_expression = str(self.token.value)
        else:
            children = self.children
            args = " ".join([str(before) for before in children])
            s_expression =  f"({self.token.type}{' ' if args else ''}{args})"
        return "'" + s_expression if self.is_quoted else s_expression


def parse(token_stream: t.TokenStream, rbp: int) -> Node:
    before = token_stream.current

    if before.type in [t.number, t.name]:         # A
        token_stream.advance()
        node = Node(before, [])

    elif before.type == "[":                      # B
        token_stream.advance()
        children = []
        while token_stream.current.type != "]":
            children.append(parse(token_stream, 0))
            if token_stream.current.type != "]":  # C
                assert token_stream.current.type == ","
                token_stream.advance()
        token_stream.advance()
        node = Node(before, children)

    else:
        raise RuntimeError

    return _parse_led(token_stream, rbp, node)


def _parse_led(token_stream: t.TokenStream, rbp: int, left: Node) -> Node:
    before = token_stream.current
    null_types = ["[", t.number, t.name, "]", t.eof, ","]

    if before.type == "===":                      # D
        if rbp >= 2:                              # E
            return left
        token_stream.advance()
        right = parse(token_stream, 2)
        return _parse_led(token_stream, rbp, Node(before, [left, right]))

    elif before.type == ".":                      # F
        if rbp >= 3:                             # G
            return left
        token_stream.advance()
        right = parse(token_stream, 3)
        return _parse_led(token_stream, rbp, Node(before, [left, right]))

    elif before.type in null_types:               # H
        return left

    raise RuntimeError


def test_demo():
    token_stream = t.TokenStream.from_source("foo.bar === [1, 2, 3]")
    assert str(parse(token_stream, 0)) == "(=== (. foo bar) ([ 1 2 3))"
