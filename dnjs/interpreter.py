from __future__ import annotations

from dataclasses import dataclass, replace
from functools import partial
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Iterator

from dnjs import builtins
from dnjs import parser as p
from dnjs import tokeniser as t


class Missing:
    def __repr__(self):
        return "<missing>"


missing = Missing()


@dataclass
class Module:
    path: str
    scope: builtins.Scope
    exports: Dict[str, builtins.Value]
    default_export: Union[Missing, builtins.Value]
    value: Union[Missing, builtins.Value]


handlers = {
    # atoms
    t.name: builtins.name_handler,
    t.d_name: lambda _, n: n.token.value,
    t.literal: lambda _, n: {"null": None, "true": True, "false": False}[n.token.value],
    t.number: lambda _, n: float(n.token.value) if "." in n.token.value else int(n.token.value),
    t.string: lambda _, n: builtins.string(n.token.value),
    t.template: lambda _, n: builtins.string(n.token.value),

    # unary
    "const": builtins.Const,
    "(": lambda _, __, a: a,
    "import": builtins.Import,
    "export": builtins.Export,
    "default": builtins.Default,
    "...": builtins.Ellipsis_,

    # binary
    "=": builtins.Assign,
    "===": builtins.equal,
    ".": builtins.dot_handler,
    "from": builtins.From,
    ":": lambda _, __, a, b: tuple((a, b)),
    t.apply: lambda _, __, a, b: a(*b),

    # ternary
    "?": builtins.ternary,

    # variadic
    "[": builtins.array_handler,
    "{": builtins.object_handler,
    "`": lambda _, __, *values: "".join(str(n) for n in values),
    t.many: lambda _, __, *values: list(values),
    t.d_brack: lambda _, __, *values: list(values),
    t.d_brace: lambda _, __, *values: list(values),
    t.d_many: lambda _, __, *values: list(values),
    "=>": lambda scope, _, a, b: partial(builtins.dnjs_function, scope, a, b),
}


def interpret_node(scope: builtins.Scope, node: p.Node):
    if node.is_quoted:
        return node
    args = [interpret_node(scope, c) for c in node.children]
    out = handlers[node.token.type](scope, node, *args)
    return out


def interpret(path: Optional[Path] = None, source: Optional[str] = None) -> Module:
    if path is None:
        token_stream = t.TokenStream.from_source(source)
    else:
        token_stream = t.TokenStream(path)
    module = Module(
        path=token_stream.filepath,
        scope=dict(builtins.default_scope),
        exports={},
        default_export=missing,
        value=missing,
    )
    for statement_node in p.parse_statements(token_stream):
        statement = interpret_node(module.scope, statement_node)

        if isinstance(statement, builtins.Const):
            name, value = statement.arg.left, statement.arg.right
            module.scope[name] = value

        elif isinstance(statement, builtins.Import):
            names, from_path = statement.arg.left, statement.arg.right
            if not from_path.startswith("."):
                continue
            if not from_path.endswith(".dn.js"):
                raise p.ParseError("can only import files ending .dn.js", statement.token)
            imported_module = interpret(module.path.parent / Path(from_path))

            if isinstance(names, str):
                if imported_module.default_export is missing:
                    raise p.ParseError(f"{imported_module.path} missing export default", statement.token)
                module.scope[names] = imported_module.default_export
            elif isinstance(names, list):
                for name in names:
                    module.scope[name] = imported_module.exports[name]
            else:
                raise RuntimeError

        elif isinstance(statement, builtins.Export):
            if isinstance(statement.arg, builtins.Const):
                name, value = statement.arg.arg.left, statement.arg.arg.right
                module.scope[name] = value
                module.exports[name] = value
            else:  # isinstance(statement.arg, builtins.Default)
                module.default_export = statement.arg.arg

        else:
            module.value = statement

    return module
