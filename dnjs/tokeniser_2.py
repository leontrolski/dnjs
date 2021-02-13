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
template = "template"

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


class TokenStreamEmptyError(RuntimeError):
    pass


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
    _is_complete: bool = False

    def advance(self, include_newlines: bool = False) -> Token:
        if self._is_complete:
            raise TokenStreamEmptyError
        if self.current.type == eof:
            self._is_complete = True
            return self.current

        token = self.current
        try:
            current = self._read()
            while not include_newlines and current.type == newline:
                current = self._read()
        except IndexError as e:
            current = Token(eof, eof, pos=self._pos, lineno=self._lineno, linepos=self._linepos)
        self.current = current
        return token

    def __post_init__(self):
        self.source = self.source.rstrip() + "\n"  # always end on one "\n"
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

        def gobble():
            before = char()
            inc()
            return before

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
        t = char()
        inc()

        if t == "\n":
            inc_line()
            return make(newline, "\n")

        if t == '"':
            while True:
                this_char = char()
                if this_char == "\n":
                    t += gobble()
                    return make(unexpected, t)
                elif this_char == "\\":
                    t += gobble()
                    t += gobble()
                elif this_char == '"':
                    t += gobble()
                    return make(literal, t)
                else:
                    t += gobble()

        if t == "`" or (t == "}" and self._template_depth):
            if t == "`":
                self._template_depth += 1
            while True:
                this_char = char()
                if this_char == "\\":
                    t += gobble()
                    t += gobble()
                elif this_char == "$":
                    t += gobble()
                    if char() == "{":
                        t += gobble()
                        return make(template, t)
                elif this_char == "`":
                    self._template_depth -= 1
                    t += gobble()
                    return make(template, t)
                elif this_char == "\n":
                    inc_line()
                    t += gobble()
                else:
                    t += gobble()

        if t in _punctuation_tree:
            tree = _punctuation_tree[t]
            while char() in tree:
                t += gobble()
            if t not in _punctuation_values:
                return make(unexpected, t)
            return make(punctuation, t)

        if t in _number_begin:
            seen_decimal_point = False
            while char() in _number_all:
                digit = char()
                inc()
                if digit == ".":
                    if seen_decimal_point:
                        t += digit
                        return make(unexpected, t)
                    seen_decimal_point= True
                t += digit
            return make(literal, t)

        if t in _name_begin:
            while char() in _name_all:
                t += gobble()
            if t in _keyword_values:
                return make(keyword, t)
            if t in _literal_values:
                return make(literal, t)
            return make(name, t)

        return make(unexpected, t)
