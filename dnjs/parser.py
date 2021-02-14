from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from textwrap import dedent
from typing import Callable, Dict, Iterator, Optional, List, Set, Tuple

import dnjs.tokeniser as t

LOW_PREC, COLON_PREC, HIGH_PREC = 1, 2, 999


@dataclass
class Node:
    token: t.Token
    children: List[Node]
    is_quoted: bool = False

    def __str__(self) -> str:
        if self.token.type in t.atoms:
            s_expression = str(self.token.value)
        else:
            children = self.children
            args = " ".join([str(c) for c in children])
            s_expression =  f"({self.token.type}{' ' if args else ''}{args})"
        return "'" + s_expression if self.is_quoted else s_expression


# prefix, infix, infix_right_assoc get populated further down
prefix: Dict[str, Tuple[Callable[[t.TokenStream, int], Node], int]] = {}
infix: Dict[str, Tuple[Callable[[t.TokenStream, int, Node], Node], int]] = {}
infix_right_assoc: Set[str] = set()


def parse(token_stream: t.TokenStream, rbp: int = 0) -> Node:
    f, _bp = prefix.get(token_stream.current.type, (raise_unexpected_error, HIGH_PREC))
    node = f(token_stream, _bp)
    return _parse_infix(token_stream, rbp, node)


def _parse_infix(token_stream: t.TokenStream, rbp: int, node: Node) -> Node:
    f, _lbp = infix.get(token_stream.current.type, (raise_unexpected_error, HIGH_PREC))
    _rbp = _lbp - 1 if token_stream.current.type in infix_right_assoc else _lbp

    if rbp >= _lbp:
        return node

    return _parse_infix(token_stream, rbp, f(token_stream, _rbp, node))


def parse_statements(token_stream: t.TokenStream) -> Iterator[Node]:
    while token_stream.current.type != t.eof:
        node = parse(token_stream)
        convert_children(Node(replace(t._void_token, type="statement"), [node]))
        yield node
        if token_stream.current.type == t.eof:
            break
        prev_lineno = max([c.token.lineno for c in _yield_descendants(node)])
        if token_stream.current.lineno <= prev_lineno:
            raise ParseError("expected statements to be on separate lines", token_stream.current)


def eat(token_stream: t.TokenStream, token_type: str) -> None:
    """Assert the value of the current token, then move to the next token."""
    token = token_stream.current
    if token_type and not token.type == token_type:
        raise ParseError(f"expected {repr(token_type)} got {repr(token.value)}", token_stream.current)
    token_stream.advance()


def prefix_atom(token_stream: t.TokenStream, bp: int) -> Node:
    before, _ = token_stream.current, token_stream.advance()
    return Node(before, [])


def prefix_unary(token_stream: t.TokenStream, bp: int) -> Node:
    before, _ = token_stream.current, token_stream.advance()
    return Node(before, [parse(token_stream, bp)])


def infix_binary(token_stream: t.TokenStream, rbp: int, left: Node) -> Node:
    """a === b becomes (=== a b)"""
    before = token_stream.current

    if before.type == "=>":
        # (a, b) => [1, 2] becomes (=> (* a b) '([ 1 2))
        # a => [1, 2] becomes (=> (* a) '([ 1 2))
        if left.token.type == t.name:
            left = Node(left.token, [left])
        left.token = replace(left.token, type=t.many)

    if before.type == "(":
        # in the case of ( as a infix binary operator, eg:
        # f(1, 2, 3) becomes ($ f (* 1 2 3))
        before = replace(before, type=t.apply)
        right = parse(token_stream, rbp)
        right.token = replace(right.token, type=t.many)
    else:
        token_stream.advance()
        right = parse(token_stream, rbp)

    if before.type == "=>":
        right.is_quoted = True

    return Node(before, [left, right])


def infix_ternary(token_stream: t.TokenStream, rbp: int, left: Node) -> Node:
    """a > 1 ? x : y becomes (? (> a 1) x y)"""
    before, _ = token_stream.current, token_stream.advance()
    true_expr = parse(token_stream, COLON_PREC)
    eat(token_stream, ":")
    false_expr = parse(token_stream, rbp)
    children = [left, true_expr, false_expr]
    true_expr.is_quoted = True
    false_expr.is_quoted = True
    return Node(before, children)


def prefix_variadic(token_stream: t.TokenStream, bp: int) -> Node:
    """{a: 1, ...x} becomes ({ (: a 1) (... x))"""
    before, _ = token_stream.current, token_stream.advance()
    end = {"[": "]", "{": "}", "(": ")"}[before.type]
    children = []
    while token_stream.current.type != end:
        child = parse(token_stream, LOW_PREC)
        children.append(child)
        if token_stream.current.type != end:
            eat(token_stream, ",")
    eat(token_stream, end)
    return Node(before, children)


def prefix_variadic_template(token_stream: t.TokenStream, bp: int) -> Node:
    """`foo ${a} ${[1, 2]} bar` becomes (` `foo ${ a } ${ ([1 2) } bar`)

    Templates are a bit weird in that Token("`foo ${") appears twice -
    as the operator and as a piece of template data.
    """
    before, _ = token_stream.current, token_stream.advance()
    children = [Node(replace(before, type=t.template), [])]
    if not before.value.endswith("`"):
        while not token_stream.current.value.endswith("`"):
            children.append(parse(token_stream, bp))
        children.append(parse(token_stream, bp))
    return Node(before, children)


def raise_unexpected_error(token_stream: t.TokenStream, *_: int) -> Node:
    raise ParseError("unexpected token", token_stream.current)


def raise_prefix_error(token_stream: t.TokenStream, _: int) -> Node:
    if token_stream.current.type == t.eof:
        raise ParseError("unexpected end of input", token_stream.current)
    raise ParseError("can't be used in prefix position", token_stream.current)


def raise_infix_error(token_stream: t.TokenStream, _: int, __: Node) -> Node:
    raise ParseError("can't be used in infix position", token_stream.current)


prefix_rules = [
    (-1, ["=", "=>", ")", "}", "]", ":", t.eof], raise_prefix_error),
    (-1, [*t.atoms, t.name], prefix_atom),
    (3, ["...", "import", "const", "export", "default"], prefix_unary),
    (9, ["`"], prefix_variadic_template),
    (20, ["[", "{", "("], prefix_variadic),
]
infix_rules = [
    (LOW_PREC, [","], raise_infix_error),
    (COLON_PREC, [":"], infix_binary),
    (9, ["from", "="], infix_binary),
    (10, ["=>"], infix_binary),
    (11, ["==="], infix_binary),
    (11, ["?"], infix_ternary),
    (20, [".", "("], infix_binary),
]
# populate infix_right_assoc, prefix, infix
infix_right_assoc.add("?")
for bp, token_types, f in prefix_rules:
    for token_type in token_types:
        prefix[token_type] = f, bp
for bp, token_types, f in infix_rules:
    for token_type in token_types:
        infix[token_type] = f, bp
for token_type in infix:
    if token_type not in prefix:
        prefix[token_type] = raise_prefix_error, 0
for token_type in prefix:
    if token_type not in infix:
        infix[token_type] = raise_infix_error, 0


value = {"(", "===", ".", "=>", "?", "[", "{", "`", t.apply, *t.atoms}
children_types = {
    "statement": ({"const", "import", "export", *value}, ),
    t.name: (),
    t.literal: (),
    t.number: (),
    t.string: (),
    t.template: (),
    t.d_name: (),
    "const": ({"="}, ),
    "import": ({"from"}, ),
    "export": ({"default", "const"}, ),
    "default": (value, ),
    "...": (value, ),
    "(": (value, ),
    "=": ({t.name: t.d_name}, value),
    "===": (value, value),
    ".": (value - {"{"}, {t.name: t.d_name}),
    "from": ({"{": t.d_brace, t.name: t.d_name}, {t.string}),
    ":": ({t.name: t.d_name, t.string: t.string}, value),
    t.apply: (value, {t.many}),
    "=>": ({t.many: t.d_many}, value - {"{"}),
    "?": (value, value, value),
    "[": ({"...", *value}, ...),
    "{": ({":", "..."}, ...),
    "`": (value, ...),
    t.many: (value, ...),
    t.d_brack: ({t.name: t.d_name}, ...),
    t.d_brace: ({t.name: t.d_name}, ...),
    t.d_many: ({t.name: t.d_name, "[": t.d_brack}, ...),
}

def convert_children(node: Node) -> Node:
    ts = children_types[node.token.type]
    if ts and ts[-1] is ...:
        ts = tuple(ts[0] for _ in node.children)
    assert len(node.children) == len(ts)
    for child, types in zip(node.children, ts):
        if child.token.type not in types:
            raise ParseError(
                message=f"token is not of type: {' '.join(types)}",
                token=child.token,
            )
        if isinstance(types, dict):
            child.token.type = types[child.token.type]
        convert_children(child)
    return node


@dataclass
class ParseError(Exception):
    message: str
    token: t.Token

    def __str__(self) -> str:
        if isinstance(self.token.filepath, Path):
            source = self.token.filepath.read_text()
            filepath = self.token.filepath
        else:
            source = t.UUID_SOURCE_MAP[self.token.filepath]
            filepath = "line"
        return dedent(f"""
            <ParserError {filepath}:{self.token.lineno}>
            {self.message}
            {(source + " ").splitlines()[self.token.lineno - 1].rstrip()}
            {"_" * self.token.linepos + "^"}
        """).strip()


def _yield_descendants(node: Node) -> Iterator[Node]:
    yield node
    for c in node.children:
        yield from _yield_descendants(c)
