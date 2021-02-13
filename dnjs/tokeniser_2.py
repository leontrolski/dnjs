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

# you should never see this
_void_token = Token(type="VOID", value="VOID", pos=0, lineno=0, linepos=0)

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
class TokenStream:
    # should never raise an error, only return "unexpected" tokens
    source: str
    filepath: Optional[str] = None
    current: Token = _void_token

    _pos: int = 0
    _lineno: int = 1
    _linepos: int = 0
    _template_depth: int = 0
    _iter: Iterator[Token] = iter([])

    def advance(self, include_newlines: bool = False) -> Token:
        while True:
            token = next(self._iter)
            if not include_newlines and token.type == newline:
                continue
            return token

    def __post_init__(self):
        self.source = self.source.rstrip() + "\n"  # always end on one "\n"

        def _iter():
            while True:
                yield self.current
                try:
                    self.current = self._read()
                except IndexError as e:
                    break
            yield Token(eof, eof, pos=self._pos, lineno=self._lineno, linepos=self._linepos)

        self._iter = _iter()
        self.advance()

    def _read(self) -> Token:
        def char() -> str:
            return self.source[self._pos]

        def inc() -> None:
            self._pos += 1
            self._linepos += 1

        def inc_line() -> None:
            self._linepos = 0
            self._lineno += 1

        def at_comment() -> bool:
            if self._pos >= len(self.source) - 1:
                return False
            return self.source[self._pos] + self.source[self._pos + 1] == "//"

        # eat up whitespace and comments
        while char() in _whitespace or at_comment():
            if at_comment():
                inc()
                inc()
                while char() != "\n":
                    inc()
            else:
                inc()

        make = partial(Token, pos=self._pos, lineno=self._lineno, linepos=self._linepos)

        token_str = char()
        inc()

        def gobble():
            nonlocal token_str
            token_str += char()
            inc()

        if token_str == "\n":
            inc_line()
            return make(newline, "\n")

        if token_str == '"':
            while True:
                c = char()
                if c == "\n":
                    gobble()
                    return make(unexpected, token_str)
                elif c == "\\":
                    gobble()
                    gobble()
                elif c == '"':
                    gobble()
                    return make(literal, token_str)
                else:
                    gobble()

        if token_str == "`" or (token_str == "}" and self._template_depth):
            if token_str == "`":
                self._template_depth += 1
            while True:
                c = char()
                if c == "\\":
                    gobble()
                    gobble()
                elif c == "$":
                    gobble()
                    if char() == "{":
                        gobble()
                        return make(template, token_str)
                elif c == "`":
                    self._template_depth -= 1
                    gobble()
                    return make(template, token_str)
                elif c == "\n":
                    inc_line()
                    gobble()
                else:
                    gobble()

        if token_str in _punctuation_tree:
            tree = _punctuation_tree[token_str]
            while char() in tree:
                gobble()
            if token_str not in _punctuation_values:
                return make(unexpected, token_str)
            return make(punctuation, token_str)

        if token_str in _number_begin:
            seen_decimal_point = False
            while char() in _number_all:
                digit = char()
                inc()
                if digit == ".":
                    if seen_decimal_point:
                        token_str += digit
                        return make(unexpected, token_str)
                    seen_decimal_point= True
                token_str += digit
            return make(literal, token_str)

        if token_str in _name_begin:
            while char() in _name_all:
                gobble()
            if token_str in _keyword_values:
                return make(keyword, token_str)
            if token_str in _literal_values:
                return make(literal, token_str)
            return make(name, token_str)

        return make(unexpected, token_str)
