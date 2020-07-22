from dataclasses import dataclass
import math
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Dict, List, Union

from . import parser


class Missing:
    def __repr__(self):
        return "<missing>"


missing = Missing()
Value = Union[dict, list, str, float, int, bool, None]
Func = Callable[..., Value]
Scope = Dict[str, Value]


@dataclass
class Module:
    path: str
    scope: Scope
    exports: Dict[str, Union[Value, Func]]
    default_export: Union[Missing, Value, Func]
    value: Union[Missing, Value, Func]


@dataclass
class Function:
    scope: Scope
    arg_names: List[str]
    return_value: parser.Value

    def __call__(self, *args: Value):
        assert len(self.arg_names) == len(args)
        scope_with_args = {**self.scope, **dict(zip(self.arg_names, args))}
        return get(scope_with_args, self.return_value)


def interpret(path: Path) -> Module:
    with open(path) as f:
        ast = parser.parse(f.read())

    module = Module(path=path, scope={}, exports={}, default_export=missing, value=missing)
    for node in ast.values:
        # import, ignoring external imports
        if isinstance(node, parser.Import):
            if not node.path.startswith("."):
                continue
            assert node.path.endswith(".dn.js")
            import_path = path.parent / Path(node.path)
            imported_module = interpret(import_path)

            if isinstance(node.var_or_destructure, parser.Var):
                assert imported_module.default_export is not missing, f"{imported_module.path} missing export default"
                module.scope[
                    node.var_or_destructure.name
                ] = imported_module.default_export
            elif isinstance(node.var_or_destructure, parser.Destructure):
                for var in node.var_or_destructure.vars:
                    module.scope[var.name] = imported_module.exports[var.name]
        # assign
        elif isinstance(node, parser.Assignment):
            module.scope[node.var.name] = get(module.scope, node.value)
        # export
        elif isinstance(node, parser.Export):
            value = get(module.scope, node.assignment.value)
            module.scope[node.assignment.var.name] = value
            module.exports[node.assignment.var.name] = value
        elif isinstance(node, parser.ExportDefault):
            module.default_export = get(module.scope, node.value)

        else:
            module.value = get(module.scope, node)

    return module


def get(scope: Scope, value: Value) -> Value:
    if value is None or isinstance(value, (str, float, int, bool)):
        return value
    if isinstance(value, list):
        return list_handler(scope, value)
    if isinstance(value, dict):
        return dict_handler(scope, value)
    if isinstance(value, parser.Var):
        return var_handler(scope, value)
    if isinstance(value, parser.Function):
        return function_handler(scope, value)
    if isinstance(value, parser.FunctionCall):
        return function_call_handler(scope, value)
    if isinstance(value, parser.TernaryEq):
        return ternary_eq_handler(scope, value)
    if isinstance(value, parser.Map):
        return map_handler(scope, value)
    if isinstance(value, parser.Filter):
        return filter_handler(scope, value)
    if isinstance(value, parser.DictMap):
        return dict_map_handler(scope, value)
    if isinstance(value, parser.FromEntries):
        return from_entries_handler(scope, value)
    if isinstance(value, parser.Node):
        return node_handler(scope, value)
    if isinstance(value, parser.Template):
        return template_handler(scope, value)
    if isinstance(value, parser.Dedent):
        return dedent_handler(scope, value)
    else:
        raise RuntimeError


def list_handler(scope: Scope, value: list) -> Value:
    out = []
    for x in value:
        if isinstance(x, parser.RestVar):
            rest_value = get(scope, x.var)
            assert isinstance(rest_value, list)
            for y in rest_value:
                out.append(get(scope, y))
        else:
            out.append(get(scope, x))
    return out


def dict_handler(scope: Scope, value: dict) -> Value:
    out = {}
    for k, v in value.items():
        if isinstance(k, parser.RestVar):
            rest_value = get(scope, k.var)
            assert isinstance(rest_value, dict)
            for u, w in rest_value.items():
                out[u] = get(scope, w)
        else:
            out[k] = get(scope, v)
    return out


def var_handler(scope: Scope, value: parser.Var) -> Value:
    path = list(reversed(value.name.split(".")))
    out = scope
    while path:
        k = path.pop()
        # handle `.length`
        if k == "length" and isinstance(out, list):
            return len(out)
        out = out[k]
    return out


def function_handler(scope: Scope, value: parser.Function) -> Value:
    return Function(
        scope=scope,
        arg_names=[a.name for a in value.args],
        return_value=value.return_value
    )


def function_call_handler(scope: Scope, value: parser.FunctionCall) -> Value:
    function = get(scope, value.var)
    values = get(scope, value.values)
    assert isinstance(function, Function)
    return function(*values)


def ternary_eq_handler(scope: Scope, value: parser.TernaryEq) -> Value:
    left = get(scope, value.left)
    right = get(scope, value.right)
    if_equal = get(scope, value.if_equal)
    if_not_equal = get(scope, value.if_not_equal)
    if isinstance(left, (float, int)) and isinstance(right, (float, int)):
        return if_equal if math.isclose(left, right) else if_not_equal
    return if_equal if left == right else if_not_equal


def map_handler(scope: Scope, value: parser.Map) -> Value:
    from_value = get(scope, value.from_value)
    assert isinstance(from_value, list)
    out = []
    for i, v in enumerate(from_value):
        to_value = get({**scope, "v": v, "i": i}, value.to_value)
        out.append(to_value)
    return out


def filter_handler(scope: Scope, value: parser.Filter) -> Value:
    from_value = get(scope, value.from_value)
    assert isinstance(from_value, list)
    out = []
    for i, v in enumerate(from_value):
        i = float(i)  # no ints in js
        if_value = get({**scope, "v": v, "i": i}, value.if_value)
        # TODO: here and in ternary, make equality as per JS
        if if_value:
            out.append(v)
    return out


def dict_map_handler(scope: Scope, value: parser.DictMap) -> Value:
    from_value = get(scope, value.from_value)
    assert isinstance(from_value, dict)
    out = []
    for i, [k, v] in enumerate(from_value.items()):
        to_value = get({**scope, "k": k, "v": v, "i": i}, value.to_value)
        out.append(to_value)
    return out


def from_entries_handler(scope: Scope, value: parser.FromEntries) -> Value:
    value = get(scope, value.value)
    assert isinstance(value, list)
    out = {}
    for k, v in value:
        assert isinstance(k, str)
        out[k] = v
    return out


def node_handler(scope: Scope, value: parser.Node) -> Value:
    values = get(scope, value.values)
    out = {"tag": "div", "attrs": {"className": ""}, "children": []}
    for p in value.properties:
        if isinstance(p, parser.Tag):
            out["tag"] = p.name
        if isinstance(p, parser.Id):
            out["attrs"]["id"] = p.name
        if isinstance(p, parser.Class):
            out["attrs"]["className"] += f" {p.name.strip()}"

    attrs, tail = [{}, values]
    if tail and not is_renderable(values[0]):
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


def template_handler(scope: Scope, value: parser.Template) -> Value:
    values = get(scope, value.values)
    return "".join(str(x) for x in values)


def dedent_handler(scope: Scope, value: parser.Dedent) -> Value:
    template_value = get(scope, value.template)
    return dedent(template_value).strip()


def is_vnode(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    return "tag" in node and "attrs" in node and "children" in node


def is_renderable(node: Any) -> bool:
    return node is None or isinstance(node, (str, float, int, list)) or is_vnode(node)
