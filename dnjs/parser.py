from __future__ import annotations

import codecs
from dataclasses import dataclass
import itertools
from textwrap import dedent
from typing import Any, Iterator, List, Optional, Tuple, Type, Union

from dnjs import tokeniser as t

@dataclass
class ParserError(RuntimeError):
    message: str
    reader: t.Reader
    token: t.Token

    def __str__(self) -> str:
        return dedent(f"""
            <ParserError {self.reader.filepath or 'line'}:{self.token.lineno}>
            {self.message}
            {self.reader.s.splitlines()[self.token.lineno - 1]}
            {" " * self.token.linepos + "^"}
        """).strip()


class Missing:
    def __repr__(self) -> str:
        return "<Missing>"

missing = Missing()

@dataclass
class _Paren:
    values: List[Value]

# TODO: remove these frozens
@dataclass(frozen=True)
class Var:
    name: str

@dataclass(frozen=True)
class RestVar:
    var: Var  # TODO: could be any Value

@dataclass
class Dnjs:
    values: List[Value]

@dataclass(frozen=True)
class Dot:
    left: Value
    right: str

@dataclass
class DictDestruct:
    vars: List[Var]

@dataclass
class Import:
    var_or_destructure: Union[Var, DictDestruct]
    path: str

@dataclass
class Assignment:
    var: Var
    value: Value

@dataclass
class ExportDefault:
    value: Value

@dataclass
class Export:
    assignment: Assignment

@dataclass
class Function:
    args: List[Var]
    return_value: Value

@dataclass
class FunctionCall:
    var: Var  # TODO: this should be a value
    values: List[Value]

@dataclass
class Eq:
    left: Value
    right: Value

@dataclass
class Ternary:
    predicate: Value
    if_true: Value
    if_not_true: Value

@dataclass
class Template:
    values: List[Union[str, Value]]

Number = Union[int, float]
Value = Union[dict, list, str, Number, bool, None, Var, Template, Function, Dot]

@dataclass
class Reader:
    iter_: Iterable[t.Token]
    s: str
    filepath: Optional[str]
    peek: Optional[t.Token] = None
    prev: Optional[t.Token] = None

    def _next(self) -> t.Token:
        while True:
            self.prev = self.peek
            token = next(self.iter_)
            if _is(token, t.NEWLINE):
                continue
            self.peek = token
            return token

    def next(self):
        try:
            self._next()
        except StopIteration:
            self.peek = None

    def throw(self, message: str, token: Optional[token] = None):
        raise ParserError(message, self, token or self.prev)

    def __repr__(self) -> str:
        return f"<Reader {self.filepath or 'in-memory'}>"

def parse(text: str, filepath: Optional[str] = None) -> Dnjs:
    iter_ = t.Reader(s=text, filepath=filepath)
    reader = Reader(iter_, s=text, filepath=filepath)
    reader.next()
    if reader.peek is None:
        return Dnjs([])
    return dnjs(reader)

def is_assignable_value(value: Any) -> bool:
    return value is None or isinstance(value, (list, str, int, float, bool, Var, Template, Var, Dot, FunctionCall, Ternary, dict, Function))

def _is(token: t.Token, *types: t.t) -> bool:
    return any((token.name == t.name) for t in types)

def is_read(reader: Reader, token: t.t, predicate: bool = True) -> bool:
    if predicate and _is(reader.peek, token):
        reader.next()
        return True
    return False

def is_not_read(reader: Reader, token: t.t, predicate: bool = True) -> bool:
    if predicate and not _is(reader.peek, token):
        reader.next()
        return True
    return False

def next_value(reader: Reader, prev_infix_token: Optional[t.Token] = None) -> Tuple[t.Token, Value]:
    token = reader.peek

    # atoms
    if is_read(reader, t.STRING):
        out = string(token)
    elif is_read(reader, t.NUMBER):
        out = number(token)
    elif is_read(reader, t.TRUE):
        out = True
    elif is_read(reader, t.FALSE):
        out = False
    elif is_read(reader, t.NULL):
        out = None
    elif is_read(reader, t.VAR):
        out = Var(token.s)

    # composite
    elif is_read(reader, t.ELLIPSIS):
        out = rest_var(reader)
    elif is_read(reader, t.PARENL):
        out = paren(reader)
    elif is_read(reader, t.BRACKL):
        out = array(reader)
    elif is_read(reader, t.BRACEL):
        out = object_(reader)
    elif is_read(reader, t.IMPORT):
        out = import_(reader)
    elif is_read(reader, t.EXPORT):
        out = export(reader)
    elif is_read(reader, t.CONST):
        out = assignment(reader)
    elif is_read(reader, t.TEMPLATE):
        out = template(reader, token)
    else:
        raise reader.throw(f"Not sure how to deal with {token.name} token: {token.s}", token)

    if isinstance(out, _Paren) and (reader.peek is None or not _is(reader.peek, t.ARROW)):
        if len(out.values) != 1:
            reader.throw("Parentheses may only contain one value")
        out = out.values[0]

    if get_precedence(reader.peek) < get_precedence(prev_infix_token):
        return out
    return infix(reader, reader.peek, out)

def get_precedence(token: Optional[t.Token]) -> int:
    if token is None:
        return 0
    return {
        t.QUESTION.name: 10,
        t.EQ.name: 20,
        t.DOT.name: 30,
    }.get(token.name, 0)

def infix(reader: Reader, token: t.Token, out: Value) -> Value:
    token = reader.peek
    was_infix = True
    if token is None:
        return out
    elif is_read(reader, t.DOT):
        out = dot(reader, out)
    elif is_read(reader, t.EQ):
        out = Eq(left=out, right=next_value(reader, prev_infix_token=token))
    elif is_read(reader, t.QUESTION):
        out = ternary(reader, out)
    elif is_read(reader, t.ARROW):
        out = function(reader, out)
    elif is_read(reader, t.PARENL):
        out = function_call(reader, out)
    else:
        was_infix = False

    if was_infix:
        out = infix(reader, reader.peek, out)

    return out

def dnjs(reader: Reader) -> Dnjs:
    _dnjs = Dnjs([])
    while True:
        value = next_value(reader)
        _dnjs.values.append(value)
        if reader.peek is None:
            break
        # TODO: check for a newline after each statement
    return _dnjs

def string(token: t.Token) -> str:
    end_ = -2 if token.s.endswith(t.dollarbrace) else -1
    return codecs.escape_decode(bytes(token.s[1:end_], "utf-8"))[0].decode("utf-8")

def number(token: t.Token) -> Number:
    return float(token.s) if "." in token.s else int(token.s)

def _bracketed(reader: Reader, end: t.t, of_token: Optional[t.t] = None) -> List[Value]:
    saw_closing = False
    i = 0
    l = []
    while True:
        if is_read(reader, end):
            saw_closing = True
            break

        if is_read(reader, t.COMMA, i % 2 == 0):
            reader.throw("Didn't expect a comma here")
        elif is_not_read(reader, t.COMMA, i % 2 == 1):
            reader.throw("Expected a comma here")
        elif is_read(reader, t.COMMA):
            pass
        else:
            if is_not_read(reader, of_token, of_token is not None):
                reader.throw(f"Expected to see variable of type: {of_token.name}")
            value = next_value(reader)
            l.append(value)
        i += 1

    if not saw_closing:
        reader.throw("Array has no closing bracket")

    return l

def paren(reader: Reader) -> _Paren:
    return _Paren(_bracketed(reader, t.PARENR))

def array(reader: Reader) -> list:
    return _bracketed(reader, t.BRACKR)

def object_(reader: Reader) -> dict:
    saw_closing = False
    i = 0
    d = {}
    current_key = missing
    while True:
        if is_read(reader, t.BRACER):
            saw_closing = True
            break

        if i % 4 == 0 and not _is(reader.peek, t.STRING, t.VAR, t.ELLIPSIS):
            reader.next()
            reader.throw("Object, expected a string here")
        elif is_not_read(reader, t.COLON, i % 4 == 1):
            reader.throw("Object, expected a colon here")
        elif is_read(reader, t.COMMA, i % 4 == 2):
            reader.throw("Object, didn't expect a comma here")
        elif is_read(reader, t.COLON, i % 4 == 2):
            reader.throw("Object, didn't expect a colon here")
        elif is_not_read(reader, t.COMMA, i % 4 == 3):
            reader.throw("Object, expected a comma here")
        elif _is(reader.peek, t.COMMA, t.COLON):
            reader.next()
        elif i % 4 == 0:
            token = reader.peek
            value = next_value(reader)
            current_key = value
            if _is(token, t.VAR):
                current_key = value.name
            elif _is(token, t.ELLIPSIS):
                d[value] = None
                current_key = missing
                i += 2  # pretend we saw `: value`
        elif i % 4 == 2:
            value = next_value(reader)
            d[current_key] = value
            current_key = missing
        i += 1

    if current_key is not missing:
        reader.throw("Object's key needs a value")
    if not saw_closing:
        reader.throw("Object has no closing brace")

    return d

def rest_var(reader: t.Readern) -> RestVar:
    value = next_value(reader)
    return RestVar(value )

def import_(reader: Reader) -> Import:
    inner_token = reader.peek
    if is_read(reader, t.VAR):
        var_or_destructure = Var(inner_token.s)
    elif is_read(reader, t.BRACEL):
        vars = _bracketed(reader, t.BRACER, of_token=t.VAR)
        var_or_destructure = DictDestruct(vars=vars)
    else:
        reader.throw("Import, expected a var or {var} here")

    if not is_read(reader, t.FROM):
        reader.throw("Import, expected from here")
    inner_token = reader.peek
    if not is_read(reader, t.STRING):
        reader.throw('Import, expected a string, eg: "../myFile.dn.js" here')

    return Import(var_or_destructure, string(inner_token))

def export(reader: Reader) -> Union[Export, ExportDefault]:
    inner_token = reader.peek
    if is_read(reader, t.DEFAULT):
        value = next_value(reader)
        if not is_assignable_value(value):
            reader.throw("Export, expected a value here")
        return ExportDefault(value)
    elif is_read(reader, t.CONST):
        return Export(assignment(reader))
    else:
        reader.throw("Export, expected a default value or const var = value")

def assignment(reader: Reader) -> Assignment:
    inner_token = reader.peek
    if not is_read(reader, t.VAR):
        reader.throw("Assignment, expected var here")
    var = Var(inner_token.s)
    if not is_read(reader, t.ASSIGN):
        reader.throw("Assignment, expected = here")
    value = next_value(reader)
    if not is_assignable_value(value):
        reader.throw("Assignment, expected a value here")
    return Assignment(var, value)

def template(reader: Reader, token: t.Token) -> Template:
    saw_closing = False
    i = 1
    l = [string(token)]

    if token.s.endswith(t.backtick):
        return Template(l)

    while True:
        if is_not_read(reader, t.TEMPLATE, i % 2 == 0):
            reader.throw("Expected more template here")
        elif i % 2 == 0:
            inner_token = reader.peek
            reader.next()
            l.append(string(inner_token))
            if inner_token.s.endswith(t.backtick):
                saw_closing = True
                break
        else:
            value = next_value(reader)
            l.append(value)
        i += 1

    if not saw_closing:
        reader.throw("Template has no final `")

    return Template(l)

# infix

def dot(reader: Reader, value: Value) -> Dot:
    inner_token = reader.peek
    if not is_read(reader, t.VAR):
        reader.throw("Expected eg: foo.bar here")
    return Dot(left=value, right=inner_token.s)

def ternary(reader: Reader, value: Value) -> Ternary:
    if_true = next_value(reader)
    if not is_read(reader, t.COLON):
        reader.throw("Expected ternary expression in the form x ? y : z")
    if_not_true = next_value(reader)
    return Ternary(predicate=value, if_true=if_true, if_not_true=if_not_true)

def function(reader: Reader, value: Value) -> Function:
    if not isinstance(value, (Var, _Paren)):
        reader.throw("Function must be defined with arguments")
    # TODO: assert the values conform to possible args
    args = value.values if isinstance(value, _Paren) else [value]
    if is_read(reader, t.BRACEL):
        reader.throw("Functions returning literal objects must enclose them in brackets, eg: x => ({a: 1})")
    return Function(args=args, return_value=next_value(reader))

def function_call(reader: Reader, value: Value) -> FunctionCall:
    # TODO: currently this supports eg. 1(foo)
    _paren = paren(reader)
    return FunctionCall(var=value, values=_paren.values)

# missing restrictions:
# what about '3 4' (with no newlines) - this should be invalid!
# Vars on their own
#
# Test every failure mode
