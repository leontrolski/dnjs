from __future__ import annotations

import codecs
from dataclasses import dataclass, replace
import functools
import math
import re
import textwrap
from typing import Any, Callable, Dict, List, Tuple, Union

from dnjs import parser


@dataclass
class InterpreterError(parser.ParseError): ...


class Undefined:
    def __repr__(self):
        return "undefined"


undefined = Undefined()
Scope = Dict[str, Any]
Func = Callable[..., "Value"]
Value = Union[dict, list, str, float, int, bool, None, Func, Undefined]


# data classes


@dataclass
class Unary:
    _: Any
    node: p.Node
    arg: Any

    def __repr__(self) -> str:
        return f"<Unary {self.node}>"


@dataclass
class Binary:
    _: Any
    node: p.Node
    left: Any
    right: Any

    def __repr__(self) -> str:
        return f"<Binary {self.node}>"


class Const(Unary): ...
class Import(Unary): ...
class Export(Unary): ...
class Default(Unary): ...
class Ellipsis_(Unary): ...
class Assign(Binary): ...
class From(Binary): ...


# operator handlers


def dnjs_function(scope: Scope, arg_names: List[str], value_node: p.Node, *args: Any) -> Callable:
    from dnjs import interpreter  # would be nice to move this
    new_scope = dict(scope)
    for arg_name, arg in zip(arg_names, args):
        if isinstance(arg_name, list):
            for nested_arg_name, nested_arg in zip(arg_name, arg):
                new_scope[nested_arg_name] = nested_arg
        else:
            new_scope[arg_name] = arg
    return interpreter.interpret_node(new_scope, replace(value_node, is_quoted=False))


def ternary(scope: Any, _: Any, predicate: bool, if_true_node: Node, if_false_node: Node) -> Any:
    from dnjs import interpreter  # would be nice to move this
    if predicate:
        return interpreter.interpret_node(scope, replace(if_true_node, is_quoted=False))
    return interpreter.interpret_node(scope, replace(if_false_node, is_quoted=False))


def string(value: str) -> str:
    end_ = -2 if value.endswith("${") else -1
    return codecs.escape_decode(bytes(value[1:end_], "utf-8"))[0].decode("utf-8")


def name_handler(scope: Scope, node: p.Node):
    if node.token.value not in scope:
        raise InterpreterError(f"variable {node.token.value} is not in scope", node.token)
    return scope[node.token.value]


def dot_handler(_: Any, node: Node, value: Any, name: str) -> Any:
    if value is undefined:
        raise InterpreterError(f"cannot get .{name}, value is undefined", node.token)

    if isinstance(value, list):
        if name == "length":
            return len(value)
        if name == "map":
            return lambda f: [f(v, i) for i, v in enumerate(value)]
        if name == "filter":
            return lambda f: [v for i, v in enumerate(value) if f(v, i)]
        if name == "reduce":
            return lambda f, initializer: functools.reduce(f, value, initializer)
        if name == "includes":
            return lambda v: v in value

    if value is default_scope["m"]:
        if name == "trust":
            return m_dot_trust

    if not isinstance(value, dict):
        return undefined

    return value.get(name, undefined)


def array_handler(_: Any, __: Any, *values: Iterator[Any]) -> List[Any]:
    out = []
    for value in values:
        if isinstance(value, Ellipsis_):
            if not isinstance(value.arg, list):
                raise InterpreterError("must be of type: [", value.node.children[0].token)
            out.extend(value.arg)
        else:
            out.append(value)
    return out


def object_handler(_: Any, __: Any, *values: Iterator[Any]) -> Dict[str, Any]:
    out = {}
    for value in values:
        if isinstance(value, Ellipsis_):
            if not isinstance(value.arg, dict):
                raise InterpreterError("must be of type: {", value.node.children[0].token)
            out.update(value.arg)
        else:
            k, v = value
            out[k] = v
    return out


# TODO: make this exactly like js
def equal(_: Any, __: Any, left: Value, right: Value) -> bool:
    if isinstance(left, (float, int)) and isinstance(right, (float, int)):
        return math.isclose(left, right)
    return left == right


# global variables


@dataclass
class TrustedHtml:
    string: str


def m_dot_trust(value: Value) -> TrustedHtml:
    assert isinstance(value, str)
    return TrustedHtml(value)


def m(properties: str, *args: List[Value]) -> Value:
    out = {"tag": "div", "attrs": {"className": ""}, "children": []}

    assert isinstance(properties, str)
    for type_, p in re.findall(r"(^|\.|#)([\w\d\-_]+)", properties):
        if type_ == "":
            out["tag"] = p
        if type_ == "#":
            out["attrs"]["id"] = p
        if type_ == ".":
            out["attrs"]["className"] += f" {p}"

    if not args:
        return out

    args = list(args)
    attrs, tail = [{}, args]
    if tail and not is_renderable(args[0]):
        attrs, *tail = tail
    if "class" in attrs:
        assert isinstance(attrs["class"], list)
        attrs = {**attrs}
        classes = attrs.pop("class")
        for c in classes:
            out["attrs"]["className"] += f" {c.strip()}"
    out["attrs"]["className"] = out["attrs"]["className"].strip()

    for k, v in attrs.items():
        out["attrs"][k] = v

    def add_children(v):
        assert is_renderable(v)
        if v is None:
            return
        if isinstance(v, list):
            for x in v:
                add_children(x)
            return
        if isinstance(v, (float, int)):
            v = str(v)
        out["children"].append(v)

    add_children(tail)

    return out


def _is_vnode(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    return "tag" in node and "attrs" in node and "children" in node


def is_renderable(node: Any) -> bool:
    return node is None or isinstance(node, (str, float, int, list, TrustedHtml)) or _is_vnode(node)


default_scope = {
    "Object": {
        "entries": lambda v: [list(n) for n in v.items()],
        "fromEntries": lambda v: dict(v)
    },
    "m": m,
    "dedent": lambda s: textwrap.dedent(s).strip(),
}

# other

def undefineds_to_none(o: Any) -> Any:
    if isinstance(o, list):
        return [undefineds_to_none(v) for v in o]
    if isinstance(o, dict):
        return {k: undefineds_to_none(v) for k, v in o.items()}
    if o is undefined:
        return None
    return o
