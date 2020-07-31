from dataclasses import asdict, is_dataclass
from html import escape
import re
from typing import Any

from bs4 import BeautifulSoup

from . import builtins, interpreter

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
SPACE_PATTERN = re.compile(r'^(\s*)', re.MULTILINE)


def make_value_js_friendly(value: interpreter.Value) -> interpreter.Value:
    if isinstance(value, dict):
        return {k: make_value_js_friendly(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_value_js_friendly(n) for n in value]
    if is_dataclass(value):
        return make_value_js_friendly(asdict(value))
    return value


def to_html(value: interpreter.Value, prettify: bool=True) -> str:
    assert builtins.is_renderable(value)
    if value is None:
        return ""
    if isinstance(value, str):
        return escape(value)
    if isinstance(value, (float, int)):
        return str(value)
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
    html_str = f"<{escape(tag)} {attrs_str}>"
    if not is_self_closing:
        html_str += ''.join(to_html(c) for c in children)
        html_str += f"</{escape(tag)}>"
    if prettify:
        html_str = BeautifulSoup(html_str, features="html.parser").prettify()
        html_str = SPACE_PATTERN.sub(r'\1\1\1\1', html_str)  # make indent width 4
    return html_str
