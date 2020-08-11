import re
import textwrap
from typing import Any, List, Tuple

from . import interpreter


# Object.methods


class Object:
    pass


def entries(v: dict) -> list:
    assert isinstance(v, dict)
    return [list(n) for n in v.items()]


def from_entries(v: List[Tuple[str, "interpreter.Value"]]) -> dict:
    assert isinstance(v, list)
    return dict(v)


# List.methods


def length(v: List["interpreter.Value"]) -> int:
    assert isinstance(v, list)
    return len(v)


def filter_(value: List["interpreter.Value"], f: "interpreter.Function") -> list:
    assert isinstance(f, interpreter.Function)
    out = []
    for i, v in enumerate(value):
        if f.first_arg_is_destructure:
            k, v = v
            if f(k, v, i):
                out.append([k, v])
        else:
            if f(v, i):
                out.append(v)
    return out


def map(value: List["interpreter.Value"], f: "interpreter.Function") -> list:
    assert isinstance(f, interpreter.Function)
    out = []
    for i, v in enumerate(value):
        if f.first_arg_is_destructure:
            k, v = v
            out.append(f(k, v, i))
        else:
            out.append(f(v, i))
    return out


def includes(value: List["interpreter.Value"], v: "interpreter.Value") -> bool:
    return v in value


# global variables


def dedent(value: str) -> str:
    return textwrap.dedent(value).strip()


def m(properties: str, *args: List["interpreter.Value"]) -> "interpreter.Value":
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
    return node is None or isinstance(node, (str, float, int, list)) or _is_vnode(node)
