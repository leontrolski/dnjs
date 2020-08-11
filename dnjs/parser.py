from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, List, Optional, Union

from lark import Lark, Transformer


with open(Path(__file__).parent / "grammar.lark") as f:
    grammar = Lark(f.read(), start="dnjs", ambiguity="explicit")


@dataclass
class _Split:
    @classmethod
    def from_tokens(cls, tokens):
        return cls(*tokens)


@dataclass(frozen=True)
class Var(_Split):
    name: str


@dataclass(frozen=True)
class RestVar(_Split):
    var: Var


def dict_handler(_, values: List[Any]) -> dict:
    values = [(n, None) if isinstance(n, RestVar) else n for n in values]
    return dict(values)


def string_handler(_, tokens) -> str:
    [s] = tokens
    return json.loads(s)


def number_handler(_, tokens) -> Union[float, int]:
    [n] = tokens
    return json.loads(n)


Value = Union[dict, list, str, float, int, bool, None, Var, RestVar]  # not sure this is true


@dataclass(frozen=True)
class Dot(_Split):
    left: Value
    right: str


@dataclass
class DictDestruct:
    vars: List[Var]


@dataclass
class ListDestruct:
    vars: List[Var]


@dataclass
class Import(_Split):
    var_or_destructure: Union[Var, DictDestruct]
    path: str


@dataclass
class Assignment(_Split):
    var: Var
    value: Value


@dataclass
class ExportDefault(_Split):
    value: Value


@dataclass
class Export(_Split):
    assignment: Assignment


@dataclass
class Function:
    args: List[Var]
    return_value: Value

    @classmethod
    def from_tokens(cls, tokens):
        [*args, return_value] = tokens
        return cls(args, return_value)


@dataclass
class FunctionCall:
    var: Var
    values: List[Value]

    @classmethod
    def from_tokens(cls, tokens):
        [var, *values] = tokens
        return cls(var, values)


@dataclass
class TernaryEq(_Split):
    left: Value
    right: Value
    if_equal: Value
    if_not_equal: Value


@dataclass
class Map(_Split):
    from_value: Value
    to_value: Value


@dataclass
class Filter(_Split):
    from_value: Value
    if_value: Value


@dataclass
class DictMap(_Split):
    from_value: Value
    to_value: Value


def template_string(_, tokens) -> str:
    [s] = tokens
    s = str(s)
    if s.startswith("`"):
        s = s[1:]
    if s.startswith("}"):
        s = s[1:]
    if s.endswith("`"):
        s = s[:-1]
    if s.endswith("${"):
        s = s[:-2]
    return s


@dataclass
class Template:
    values: List[Union[str, Var]]


@dataclass
class Dnjs:
    values: List[Value]


class TreeToJson(Transformer):
    dnjs = Dnjs
    var = Var.from_tokens
    basic_var = Var.from_tokens
    rest_var = RestVar.from_tokens
    dot = Dot.from_tokens
    dict_destruct = DictDestruct
    list_destruct = ListDestruct
    import_ = Import.from_tokens
    assignment = Assignment.from_tokens
    export_default = ExportDefault.from_tokens
    export = Export.from_tokens
    function = Function.from_tokens
    ternary_eq = TernaryEq.from_tokens
    function_call = FunctionCall.from_tokens
    template_string = template_string
    template = Template
    CNAME = str
    string = string_handler
    number = number_handler
    list = list
    pair = tuple
    dict = dict_handler
    null = lambda _, __: None
    true = lambda _, __: True
    false = lambda _, __: False


def pre_parse(text: str) -> Lark:
    return grammar.parse(text + "\n")


def parse(text: str) -> Dnjs:
    tree = pre_parse(text)
    return TreeToJson().transform(tree)
