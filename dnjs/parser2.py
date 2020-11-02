from __future__ import annotations

import codecs
from dataclasses import dataclass
import itertools
from textwrap import dedent
from typing import Any, Iterator, List, Optional, Tuple, Union

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

@dataclass(frozen=True)
class Var:
    name: str

@dataclass(frozen=True)
class RestVar:
    var: Var

@dataclass
class Dnjs:
    values: List[Value]

@dataclass
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
    var: Var
    values: List[Value]

# @dataclass
# class TernaryEq:
#     left: Value
#     right: Value
#     if_equal: Value
#     if_not_equal: Value

# @dataclass
# class Map:
#     from_value: Value
#     to_value: Value

# @dataclass
# class Filter:
#     from_value: Value
#     if_value: Value

# @dataclass
# class DictMap:
#     from_value: Value
#     to_value: Value

@dataclass
class Template:
    values: List[Union[str, Value]]

Number = Union[int, float]
Value = Union[dict, list, str, Number, bool, None, Var, Template, Function, Dot]

@dataclass
class Reader:
    iter_with_next: Iterable[Tuple[t.Token, Optional[t.Token]]]
    s: str
    filepath: Optional[str]
    _current_token: Optional[t.Token] = None

    def next(self, ignore_newlines: bool = True) -> Tuple[t.Token, Optional[t.Token]]:
        while True:
            token, next_token = next(self.iter_with_next)
            if ignore_newlines and _is(token, t.NEWLINE):
                continue
            self._current_token = token
            return token, next_token

    def throw(self, message: str):
        raise ParserError(message, self, self._current_token)

def parse(text: str, filepath: Optional[str] = None) -> Dnjs:
    token_reader = t.Reader(s=text, filepath=filepath)
    current_tokens, next_tokens = itertools.tee(token_reader, 2)
    next(next_tokens)
    iter_with_next = itertools.zip_longest(current_tokens, next_tokens)
    return dnjs(Reader(iter_with_next, s=text, filepath=filepath))

def is_assignable_value(value: Any) -> bool:
    return isinstance(value, (dict, list, str, int, float, bool, None, Var, Template, Function, Dot))

def _is(token: t.Token, *types: t.t) -> bool:
    return any((token.name == t.name) for t in types)

def next_value(reader: Reader, passthru: Tuple[Token, ...] = ()) -> Tuple[t.Token, Value]:
    token, next_token = reader.next()
    out = missing

    # atoms
    if _is(token, t.STRING):
        out = string(token)
    elif _is(token, t.NUMBER):
        out = number(token)
    elif _is(token, t.TRUE):
        out = True
    elif _is(token, t.FALSE):
        out = False
    elif _is(token, t.NULL):
        out = None
    elif _is(token, t.VAR):
        out = Var(token.s)

    # composite
    elif _is(token, t.ELLIPSIS):
        out = rest_var(reader)
    elif _is(token, t.BRACKL):
        out = array(reader)
    elif _is(token, t.BRACEL):
        out = object_(reader)
    elif _is(token, t.IMPORT):
        out = import_(reader)
    elif _is(token, t.EXPORT):
        out = export(reader)
    elif _is(token, t.CONST):
        out = assignment(reader)

    elif not _is(token, *passthru):
        raise ParserError(f"Not sure how to deal with {token.name} token: {token.s}", reader, token)

    return token, lookahead(reader, next_token, out)

def dnjs(reader: Reader) -> Dnjs:
    _dnjs = Dnjs([])
    while True:
        try:
            _, value = next_value(reader)
            _dnjs.values.append(value)
            # check for a newline after each statement
            token, _ = reader.next(ignore_newlines=False)
            if not _is(token, t.NEWLINE):
                reader.throw('Expected newline after statement')
        except StopIteration:
            break
    return _dnjs

def string(token: t.Token) -> str:
    end_ = -2 if token.s.endswith(t.dollarbrace) else -1
    return codecs.escape_decode(bytes(token.s[1:end_], "utf-8"))[0].decode("utf-8")

def number(token: t.Token) -> Number:
    return float(token.s) if "." in token.s else int(token.s)

def array(reader: Reader) -> list:
    saw_closing = False
    i = 0
    l = []
    while True:
        inner_token, value = next_value(reader, passthru=(t.COMMA, t.BRACKR))
        if _is(inner_token, t.BRACKR):
            saw_closing = True
            break
        elif i % 2 == 0 and _is(inner_token, t.COMMA):
            reader.throw("Array, didn't expect a comma here")
        elif i % 2 == 1 and not _is(inner_token, t.COMMA):
            reader.throw("Array, expected a comma here")
        elif _is(inner_token, t.COMMA):
            pass
        else:
            l.append(value)
        i += 1

    if not saw_closing:
        reader.throw("Array has no closing bracket")

    return l

def object_(reader: Reader) -> dict:
    saw_closing = False
    i = 0
    d = {}
    current_key = missing
    while True:
        inner_token, value = next_value(reader, passthru=(t.COMMA, t.COLON, t.BRACER))
        if _is(inner_token, t.BRACER):
            saw_closing = True
            break
        elif i % 4 == 0 and not _is(inner_token, t.STRING, t.VAR, t.ELLIPSIS):
            reader.throw("Object, expected a string here")
        elif i % 4 == 1 and not _is(inner_token, t.COLON):
            reader.throw("Object, expected a colon here")
        elif i % 4 == 2 and _is(inner_token, t.COMMA):
            reader.throw("Object, didn't expect a comma here")
        elif i % 4 == 2 and _is(inner_token, t.COLON):
            reader.throw("Object, didn't expect a colon here")
        elif i % 4 == 3 and not _is(inner_token, t.COMMA):
            reader.throw("Object, expected a comma here")
        elif _is(inner_token, t.COMMA, t.COLON):
            pass
        elif i % 4 == 0:
            current_key = value
            if _is(inner_token, t.VAR):
                current_key = value.name
            elif _is(inner_token, t.ELLIPSIS):
                d[value] = None
                current_key = missing
                i += 2  # pretend we saw `: value`
        elif i % 4 == 2:
            d[current_key] = value
            current_key = missing
        i += 1

    if current_key is not missing:
        reader.throw("Object's key needs a value")
    if not saw_closing:
        reader.throw("Object has no closing brace")

    return d

def rest_var(reader: t.Readern) -> RestVar:
    inner_token, _ = reader.next()
    if not _is(inner_token, t.VAR):
        reader.throw("Rest, ...var")
    return RestVar(Var(inner_token.s))

def import_(reader: Reader) -> Import:
    inner_token, _ = reader.next()
    if _is(inner_token, t.VAR):
        var_or_destructure = Var(inner_token.s)
    elif _is(inner_token, t.BRACEL):
        var_or_destructure = DictDestruct(vars=[])
        for i in itertools.count():
            inner_token, _ = reader.next()
            if _is(inner_token, t.BRACER):
                break
            elif i % 2 == 0 and _is(inner_token, t.COMMA):
                reader.throw("Import, didn't expect a comma here")
            elif i % 2 == 1 and not _is(inner_token, t.COMMA):
                reader.throw("Import, expected a comma here")
            elif _is(inner_token, t.COMMA):
                pass
            elif _is(inner_token, t.VAR):
                var_or_destructure.vars.append(Var(inner_token.s))
            else:
                reader.throw("Import, expected a var here")
    else:
        reader.throw("Import, expected a var or {var} here")

    inner_token, _ = reader.next()
    if not _is(inner_token, t.FROM):
        reader.throw("Import, expected from here")

    inner_token, _ = reader.next()
    if not _is(inner_token, t.STRING):
        reader.throw('Import, expected a string, eg: "../myFile.dn.js" here')

    return Import(var_or_destructure, string(inner_token))

def export(reader: Reader) -> Union[Export, ExportDefault]:
    inner_token, _ = reader.next()
    if _is(inner_token, t.DEFAULT):
        inner_token, value = next_value(reader)
        if not is_assignable_value(value):
            reader.throw("Export, expected a value here")
        return ExportDefault(value)
    elif _is(inner_token, t.CONST):
        return Export(assignment(reader))
    else:
        reader.throw("Export, expected a default value or const var = value")

def assignment(reader: Reader) -> Assignment:
    inner_token, _ = reader.next()
    if not _is(inner_token, t.VAR):
        reader.throw("Assignment, expected var here")
    var = Var(inner_token.s)

    inner_token, _ = reader.next()
    if not _is(inner_token, t.ASSIGN):
        reader.throw("Assignment, expected = here")

    _, value = next_value(reader)
    if not is_assignable_value(value):
        reader.throw("Assignment, expected a value here")
    return Assignment(var, value)

# TODO: this needs testing with eg. (() => foo)().bar().baz or whatevs
def lookahead(reader: Reader, token: t.Token, out: Value) -> Dot:
    if _is(token, t.DOT):
        reader.next()
        token, next_token = reader.next()
        if not _is(token, t.VAR):
            reader.throw("Expected eg foo.bar here")
        return lookahead(reader, next_token, Dot(left=out, right=token.s))
    return out

# missing restrictions:
# what about '3 4' (with no newlines) - this should be invalid!
# Vars on their own
#
# Test every failure mode
