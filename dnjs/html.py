from dataclasses import asdict, is_dataclass
from html import escape
import re
from typing import Any, Callable

from dnjs import builtins

SELF_CLOSING = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def make_value_js_friendly(value: builtins.Value) -> builtins.Value:
    if value is None or isinstance(value, (float, int, bool, str, builtins.TrustedHtml)):
        return value
    if isinstance(value, dict):
        return {k: make_value_js_friendly(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_value_js_friendly(n) for n in value]
    # we turn functions into null
    if isinstance(value, Callable):
        return None
    if is_dataclass(value):
        return make_value_js_friendly(asdict(value))
    # handle pydantic without importing it
    if hasattr(value, "dict") and callable(value.dict):
        return make_value_js_friendly(value.dict())
    raise RuntimeError(f"unable to make type jsonable {type(value)}")


def to_html(value: builtins.Value, indent: int = 0) -> str:
    assert builtins.is_renderable(value)
    if value is None:
        return ""
    if isinstance(value, builtins.TrustedHtml):
        return ("    " * indent) + value.string
    if isinstance(value, str):
        return ("    " * indent) + escape(value)
    if isinstance(value, (float, int)):
        return ("    " * indent) + str(value)
    # else is vnode
    tag = value["tag"]
    attrs = {**value["attrs"]}
    children = value["children"]

    attrs_str = ""
    for k, v in attrs.items():
        if k == "className":
            k = "class"
            if not v:
                continue
        if v is None or v is False:
            pass
        elif v is True:
            attrs_str += f' {escape(k)}'
        elif isinstance(v, (float, int)):
            attrs_str += f' {escape(k)}="{str(v)}"'
        elif isinstance(v, str):
            attrs_str += f' {escape(k)}="{escape(v)}"'
        else:
            raise RuntimeError(f"unable to convert type {type(v)}")

    is_self_closing = tag in SELF_CLOSING and not children
    html_str = ("    " * indent) + f"<{escape(tag)}{attrs_str}>\n"
    if not is_self_closing:
        if tag in {"pre", "code", "textarea"}:
            html_str = html_str[:-1]  # strip \n
            html_str += "".join(to_html(c, 0) for c in children)
            html_str += f"</{escape(tag)}>\n"
        else:
            html_str += "".join(to_html(c, indent + 1) for c in children) + "\n"
            html_str += ("    " * indent) + f"</{escape(tag)}>\n"
    return html_str
