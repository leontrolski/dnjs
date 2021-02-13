from dataclasses import dataclass
from functools import partial
from typing import Iterator, Optional
import string


@dataclass
class Token:
    type: str
    value: str
    # these are all from the start of the token
    pos: int
    lineno: int
    linepos: int


# token types
eof = "eof"
newline = "newline"
unexpected = "unexpected"
keyword = "keyword"  # import from export default const
name = "name"
punctuation = "punctuation"  # = => ( ) { } [ ] , : . ... ? ===
literal = "literal"  # null true false str int float
template = "template"  # ` ${ }

_whitespace = set(" \t\f\r")  # note no \n
_number_begin = set("-" + string.digits)
_number_all = set("." + string.digits)
_name_begin = set("_" + string.ascii_letters)
_name_all = set("_" + string.ascii_letters + string.digits)
_literal_values = ["null", "true", "false"]
_keyword_values = ["import", "from", "export", "default", "const"]
_punctuation_values = ["=", "=>", "(", ")", "{", "}", "[", "]", ",", ":", ".", "...", "?", "==="]
_punctuation_tree = {}
for p in _punctuation_values:
    tree = _punctuation_tree
    for character in p:
        if character not in tree:
            tree[character] = {}
        tree = tree[character]


@dataclass
class _UnexpectedEOF(RuntimeError):
    token: Token


class _SafeEOF(str):
    def __getitem__(self, n) -> Optional[str]:
        try:
            return super().__getitem__(n)
        except IndexError as e:
            return None


@dataclass
class TokenStream:
    # should never raise an error, only return UNEXPECTED tokens
    source: str
    filepath: Optional[str] = None
    _pos: int = 0
    _lineno: int = 1
    _linepos: int = 0
    _template_depth: int = 0
    _iter: Iterator[Token] = iter([])
    current: Token = Token(
        type="MISSING",
        value="MISSING",
        pos=-1,
        lineno=-1,
        linepos=-1,
    )

    def advance(self, include_newlines: bool = False) -> Token:
        while True:
            token = next(self._iter)
            if not include_newlines and token.type == newline:
                continue
            return token

    def __post_init__(self):
        self.source = _SafeEOF(self.source.rstrip() + "\n")  # always end on a "\n"
        self._iter = self._make_iter()
        self.advance()

    def _inc(self) -> None:
        self._pos += 1
        self._linepos += 1

    def _incline(self) -> None:
        self._linepos = 0
        self._lineno += 1

    @property
    def _char(self) -> str:
        return self.source[self._pos]

    @property
    def _at_comment(self):
        return (self._char or "") + (self.source[self._pos + 1] or "") == "//"

    def _read(self) -> Token:
        while self._char in _whitespace or self._at_comment:
            if self._at_comment:
                self._inc()
                self._inc()
                while self._char != "\n":
                    self._inc()
            else:
                self._inc()

        make = partial(Token, pos=self._pos, lineno=self._lineno, linepos=self._linepos)
        token_str = self._char
        self._inc()

        def gobble():
            nonlocal token_str
            if self._char is None:
                raise _UnexpectedEOF(make(unexpected, token_str))
            token_str += self._char
            self._inc()

        if token_str is None:
            return make(eof, eof)

        if token_str == "\n":
            self._incline()
            return make(newline, "\n")

        if token_str == '"':
            while True:
                char = self._char
                if char == "\n":
                    gobble()
                    return make(unexpected, token_str)
                elif char == "\\":
                    gobble()
                    gobble()
                elif char == '"':
                    gobble()
                    return make(literal, token_str)
                else:
                    gobble()

        if token_str == "`" or (token_str == "}" and self._template_depth):
            dollar, brace = "${"
            if token_str == "`":
                self._template_depth += 1
            while True:
                char = self._char
                if char == "\\":
                    gobble()
                    gobble()
                elif char == dollar:
                    gobble()
                    if self._char == brace:
                        gobble()
                        return make(template, token_str)
                elif char == "`":
                    self._template_depth -= 1
                    gobble()
                    return make(template, token_str)
                elif char == "\n":
                    self._incline()
                    gobble()
                else:
                    gobble()

        if token_str in _punctuation_tree:
            tree = _punctuation_tree[token_str]
            while self._char in tree:
                gobble()
            if token_str not in _punctuation_values:
                return make(unexpected, token_str)
            return make(punctuation, token_str)

        if token_str in _number_begin:
            seen_decimal_point = False
            while self._char in _number_all:
                digit = self._char
                self._inc()
                if digit == ".":
                    if seen_decimal_point:
                        token_str += digit
                        return make(unexpected, token_str)
                    seen_decimal_point= True
                token_str += digit
            return make(literal, token_str)

        if token_str in _name_begin:
            while self._char in _name_all:
                gobble()
            if token_str in _keyword_values:
                return make(keyword, token_str)
            if token_str in _literal_values:
                return make(literal, token_str)
            return make(name, token_str)

        return make(unexpected, token_str)

    def _make_iter(self):
        while True:
            before = self.current
            try:
                self.current = self._read()
                if self.current.type == eof:
                    yield before
                    break
                else:
                    yield before
            except _UnexpectedEOF as e:
                self.current = e.token
                yield before
                break
