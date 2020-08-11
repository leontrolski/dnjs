from dataclasses import dataclass
from functools import partial
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Union

from . import builtins, parser


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
    first_arg_is_destructure: bool = False

    def __call__(self, *args: Value):
        assert len(self.arg_names) == len(args)
        scope_with_args = {**self.scope, **dict(zip(self.arg_names, args))}
        return get(scope_with_args, self.return_value)


@dataclass
class MakeFunction:
    f: Callable[[], Value]

    def __call__(self, *args: Value):
        return self.f(*args)


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
            elif isinstance(node.var_or_destructure, parser.DictDestruct):
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
    if isinstance(value, parser.Dot):
        return dot_handler(scope, value)
    if isinstance(value, parser.Function):
        return function_handler(scope, value)
    if isinstance(value, parser.FunctionCall):
        return function_call_handler(scope, value)
    if isinstance(value, parser.TernaryEq):
        return ternary_eq_handler(scope, value)
    if isinstance(value, parser.Template):
        return template_handler(scope, value)
    else:
        raise RuntimeError(f"unsupported value type: {type(value)}.\n{value.pretty()}")


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
    if value.name == "Object" and "Object" not in scope:
        return builtins.Object
    if value.name == "m" and "m" not in scope:
        return MakeFunction(builtins.m)
    if value.name == "dedent" and "dedent" not in scope:
        return MakeFunction(builtins.dedent)
    return scope[value.name]


def dot_handler(scope: Scope, value: parser.Dot) -> Value:
    left = get(scope, value.left)
    name = value.right.name

    if isinstance(left, list):
        if name == "length":
            return builtins.length(left)
        if name == "map":
            return MakeFunction(partial(builtins.map, left))
        if name == "filter":
            return MakeFunction(partial(builtins.filter_, left))
        if name == "includes":
            return MakeFunction(partial(builtins.includes, left))

    if left is builtins.Object:
        if name == "fromEntries":
            return MakeFunction(builtins.from_entries)
        if name == "entries":
            return MakeFunction(builtins.entries)

    return left[name]


def function_handler(scope: Scope, value: parser.Function) -> Value:
    arg_names = []
    first = next(iter(value.args), None)
    first_arg_is_destructure = isinstance(first, parser.ListDestruct)
    if first_arg_is_destructure:
        for var in first.vars:
            arg_names.append(var.name)
    for var in value.args[1:] if first_arg_is_destructure else value.args:
        arg_names.append(var.name)
    return Function(
        scope=scope,
        arg_names=arg_names,
        return_value=value.return_value,
        first_arg_is_destructure=first_arg_is_destructure,
    )


def function_call_handler(scope: Scope, value: parser.FunctionCall) -> Value:
    function = get(scope, value.var)
    values = get(scope, value.values)
    assert isinstance(function, Function) or isinstance(function, MakeFunction)
    return function(*values)


def ternary_eq_handler(scope: Scope, value: parser.TernaryEq) -> Value:
    left = get(scope, value.left)
    right = get(scope, value.right)
    if_equal = get(scope, value.if_equal)
    if_not_equal = get(scope, value.if_not_equal)
    if isinstance(left, (float, int)) and isinstance(right, (float, int)):
        return if_equal if math.isclose(left, right) else if_not_equal
    return if_equal if left == right else if_not_equal


def template_handler(scope: Scope, value: parser.Template) -> Value:
    values = get(scope, value.values)
    return "".join(str(x) for x in values)
