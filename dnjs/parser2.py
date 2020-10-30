import codecs
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, List, Optional, Union

from dnjs import tokeniser as t

@dataclass
class Var:
    name: str


@dataclass
class RestVar:
    var: Var


@dataclass
class ParserError(RuntimeError):
    message: str
    text: str
    filepath: Optional[str]
    token: t.Token

    def __str__(self) -> str:
        return dedent(f"""
            <ParserError {self.filepath or 'line'}:{self.token.lineno}>
            {self.message}
            {self.text.splitlines()[self.token.lineno - 1]}
            {" " * self.token.linepos + "^"}
        """).strip()


Value = Union[dict, list, str, float, int, bool, None, Var, RestVar]  # not sure this is true


def convert_string(token: t.Token) -> str:
    s = str(token.s)
    if s.startswith(t.backtick) or s.startswith(t.quote):
        s = s[1:]
    if s.startswith(t.bracer):
        s = s[1:]
    if s.endswith(t.backtick) or s.endswith(t.quote):
        s = s[:-1]
    if s.endswith(t.dollarbrace):
        s = s[:-2]
    return codecs.escape_decode(bytes(s, "utf-8"))[0].decode("utf-8")

@dataclass
class Dnjs:
    values: List[Value]


def parse(text: str, filepath: Optional[str] = None) -> Dnjs:
    if not text.strip():
        return Dnjs([])

    reader = t.Reader(text)
    values = []
    for token in reader:
        if token.name is t.STRING.name:
            values.append(convert_string(token))
        else:
            raise ParserError(f"Not sure how to deal with token: {token.s}", text, filepath, token)

    return Dnjs(values)
