from dataclasses import dataclass
from functools import partial, lru_cache
from pathlib import Path
from typing import Dict, Iterator, Optional, Union
from string import ascii_letters, digits
import uuid


@dataclass
class Token:
    type: str
    value: str
    filepath: Optional[Path]
    pos: int
    lineno: int
    linepos: int


# you should never see this
_void_token = Token(type="VOID", value="VOID", filepath=None, pos=0, lineno=0, linepos=0)

# token types
name, string, number, template, literal = "name", "string", "number", "template", "literal"
# = => ( ) { } [ ] , : . ... ? === import from export default const `
eof = "\x03"  # end of text character
unexpected = "unexpected"
apply = "$"
many = "*"
d_name, d_many, d_brack, d_brace = "dname", "d*", "d[", "d{"
atoms = {name, string, number, template, literal, d_name}


whitespace = set(" \t\f\r")  # note no \n
_number_begin = set("-" + digits)
_number_all = set("." + digits)
_name_begin = set("_" + ascii_letters)
_name_all = set("_" + ascii_letters + digits)
_literal_values = ["null", "true", "false"]
_keyword_values = ["import", "from", "export", "default", "const"]
_punctuation_values = ["=", "(", ")", "{", "}", "[", "]", ",", ":", ".", "?", "=>", "...", "==="]
_interim_punctuation_values = ["..", "=="]

class TokenStreamEmptyError(RuntimeError):
    pass


UUID_SOURCE_MAP: Dict[uuid.UUID, str] = {}


@dataclass
class TokenStream:
    # should never raise an error, only return "unexpected" tokens
    filepath: Union[Path, uuid.UUID]
    current: Token = _void_token

    _source: Optional[str] = None
    _pos: int = 0
    _lineno: int = 1
    _linepos: int = 0
    _template_depth: int = 0

    @classmethod
    def from_source(cls, source: str):
        source_uuid = uuid.uuid4()
        UUID_SOURCE_MAP[source_uuid] = source.rstrip()
        return cls(filepath=source_uuid)

    @property
    def source(self) -> str:
        if isinstance(self.filepath, uuid.UUID):
            return UUID_SOURCE_MAP[self.filepath]
        if self._source is None:
            self._source = self.filepath.read_text().rstrip()
        return self._source

    def advance(self) -> None:
        if self.current.type == eof:
            return
        current = self._read()
        while current.type == "\n":
            current = self._read()
        self.current = current

    def __post_init__(self):
        self.advance()

    def __repr__(self) -> str:
        return f"<TokenStream file:{self.filepath}>"

    def _read(self) -> Token:
        def char() -> str:
            if self._pos == len(self.source):
                return eof
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
        while char() in whitespace or at_comment():
            if at_comment():
                inc()
                inc()
                while char() not in {"\n", eof}:
                    inc()
            else:
                inc()

        make = partial(Token, pos=self._pos, filepath=self.filepath, lineno=self._lineno, linepos=self._linepos)
        t = char()
        inc()

        if t == eof:
            return make(eof, eof)

        if t == "\n":
            inc_line()
            return make("\n", "\n")

        if t == '"':
            while True:
                this_char = char()
                if this_char == eof:
                    return make(unexpected, t)
                if this_char == "\n":
                    t += gobble()
                    return make(unexpected, t)
                elif this_char == "\\":
                    gobble()
                    t += gobble()
                elif this_char == '"':
                    t += gobble()
                    return make(string, t)
                else:
                    t += gobble()

        if t == "`" or (t == "}" and self._template_depth):
            if t == "`":
                self._template_depth += 1
            while True:
                this_char = char()
                if this_char == eof:
                    return make(unexpected, t)
                if this_char == "\\":
                    gobble()
                    t += gobble()
                elif this_char == "$":
                    t += gobble()
                    if char() == "{":
                        t += gobble()
                        return make("`" if  t[0] == "`" else template, t)
                elif this_char == "`":
                    self._template_depth -= 1
                    t += gobble()
                    return make("`" if  t[0] == "`" else template, t)
                elif this_char == "\n":
                    inc_line()
                    t += gobble()
                else:
                    t += gobble()

        if t in _punctuation_values:
            if t + char() in _punctuation_values + _interim_punctuation_values:
                t += gobble()
                if t + char() in _punctuation_values:
                    t += gobble()
                    return make(t, t)
                if t in _interim_punctuation_values:
                    return make(unexpected, t)
                return make(t, t)
            return make(t, t)

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
            return make(number, t)

        if t in _name_begin:
            while char() in _name_all:
                t += gobble()
            if t in _keyword_values:
                return make(t, t)
            if t in _literal_values:
                return make(literal, t)
            return make(name, t)

        return make(unexpected, t)
