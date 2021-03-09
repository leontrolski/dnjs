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


def parse(token_stream: t.TokenStream, rbp: int, i) -> Node:
    print("    " * i + f"parse(rbp={rbp}) before is {token_stream.current.value}")
    before = token_stream.current

    if before.type in [t.number, t.name]:
        print("    " * i + f"hit number|name branch")
        token_stream.advance()
        node = Node(before, [])

    elif before.type == "[":
        print("    " * i + f"hit [ branch")
        token_stream.advance()
        children = []
        while token_stream.current.type != "]":
            children.append(parse(token_stream, 0, i + 1))
            print()
            if token_stream.current.type != "]":
                assert token_stream.current.type == ","
                token_stream.advance()
        token_stream.advance()
        node = Node(before, children)

    else:
        raise RuntimeError

    out = _parse_infix(token_stream, rbp, node, i + 1)
    print("    " * i + f"return {out}")
    return out


def _parse_infix(token_stream: t.TokenStream, rbp: int, left: Node, i) -> Node:
    print("    " * i + f"infix(rbp={rbp}, left={left}) before is {token_stream.current.value or 'eof'}")
    before = token_stream.current

    if before.type == "===":
        print("    " * i + f"hit === branch")
        if rbp >= 2:
            print("    " * i + f"hit high precedence branch")
            print("    " * i + f"return {left}")
            return left
        token_stream.advance()
        right = parse(token_stream, 2, i + 1)
        print()
        node = _parse_infix(token_stream, rbp, Node(before, [left, right]), i + 1)
        print("    " * i + f"return {node}")
        return node

    if before.type == ".":
        print("    " * i + f"hit . branch")
        if rbp >= 3:
            print("    " * i + f"hit high precedence branch")
            print("    " * i + f"return {left}")
            return left
        token_stream.advance()
        right = parse(token_stream, 3, i + 1)
        print()
        node = _parse_infix(token_stream, rbp, Node(before, [left, right]), i + 1)
        print("    " * i + f"return {node}")
        return node


    print("    " * i + f"didn't hit any branch")
    print("    " * i + f"return {left}")
    return left


def test_demo():
    token_stream = t.TokenStream.from_source("foo.bar === [1, 2, 3]")
    assert str(parse(token_stream, 0, 0)) == "(=== (. foo bar) ([ 1 2 3))"
