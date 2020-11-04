from collections import namedtuple
from dataclasses import dataclass
from functools import partial
from textwrap import dedent
from typing import Iterator, List, Optional, Tuple
import string

t = namedtuple("TokenConstructor", ["name", "s"])

# special
EMPTYFILE = t("EMPTYFILE", "")
EOF = t("EOF", "")
UNEXPECTED = lambda v: t("UNEXPECTED", v)
NEWLINE = t("NEWLINE", "\n")

# keyword
IMPORT = t("IMPORT", "import")
FROM = t("FROM", "from")
EXPORT = t("EXPORT", "export")
DEFAULT = t("DEFAULT", "default")
CONST = t("CONST", "const")
NULL = t("NULL", "null")
TRUE = t("TRUE", "true")
FALSE = t("FALSE", "false")
keyword_map = {token.s: token for token in (IMPORT, FROM, EXPORT, DEFAULT, CONST, NULL, TRUE, FALSE)}

# punctuation
ASSIGN = t("ASSIGN", "=")
ARROW = t("ARROW", "=>")
PARENL = t("PARENL", "(")
PARENR = t("PARENR", ")")
BRACEL = t("BRACEL", "{")
BRACER = t("BRACER", "}")
BRACKL = t("BRACKL", "[")
BRACKR = t("BRACKR", "]")
COMMA = t("COMMA", ",")
COLON = t("COLON", ":")
DOT = t("DOT", ".")
ELLIPSIS  = t("ELLIPSIS", "...")
QUESTION  = t("QUESTION", "?")
EQ = t("EQ", "===")
punctuation_map = {token.s: token for token in (ASSIGN, ARROW, PARENL, PARENR, BRACEL, BRACER, BRACKL, BRACKR, COMMA, COLON, DOT, ELLIPSIS, QUESTION, EQ)}
punctuation_tree = {}
for p in punctuation_map:
    tree = punctuation_tree
    for character in p:
        if character not in tree:
            tree[character] = {}
        tree = tree[character]

# "dynamic"
NUMBER = lambda v: t("NUMBER", v)
VAR = lambda v: t("VAR", v)
STRING = lambda v: t("STRING", v)
TEMPLATE = lambda v: t("TEMPLATE", v)
NUMBER.name = "NUMBER"
VAR.name = "VAR"
STRING.name = "STRING"
TEMPLATE.name = "TEMPLATE"

ws = set(" \t\f\r")  # note no \n
number_begin = set("-" + string.digits)
number_all = set("." + string.digits)
var_begin = set("_" + string.ascii_letters)
var_all = set("_" + string.ascii_letters + string.digits)
# quote-y
esc = "\\"
quote = '"'
backtick = "`"
dollarbrace = "${"
bracer = "}"
# misc
newline = "\n"
comment = "//"
dot = "."


@dataclass
class Token:
    name: str
    s: str
    # these are all for the start of the token
    pos: int
    lineno: int
    linepos: int


@dataclass
class UnexpectedEOF(RuntimeError):
    token: Token


class SafeEOF(str):
    def __getitem__(self, n) -> Optional[str]:
        try:
            return super().__getitem__(n)
        except IndexError as e:
            return None


@dataclass
class Reader:
    # use as an iterator, everything else is private really
    # should never raise an error, only return UNEXPECTED tokens

    s: str
    filepath: Optional[str] = None
    pos: int = 0
    lineno: int = 1
    linepos: int = 0
    template_depth: int = 0

    def __post_init__(self):
        self.s = SafeEOF(self.s.rstrip() + newline)  # always end on a newline

    def inc(self) -> None:
        self.pos += 1
        self.linepos += 1

    def incline(self) -> None:
        self.linepos = 0
        self.lineno += 1

    @property
    def this(self) -> str:
        return self.s[self.pos]

    @property
    def at_comment(self):
        return (self.this or "") + (self.s[self.pos + 1] or "") == comment

    def next(self) -> str:
        this = self.this
        self.inc()
        return this

    def skip(self):
        while self.this in ws or self.at_comment:
            if self.at_comment:
                self.inc()
                self.inc()
                while self.this != newline:
                    self.inc()
            else:
                self.inc()

    def read(self) -> Token:
        self.skip()
        make = partial(Token, pos=self.pos, lineno=self.lineno, linepos=self.linepos)
        token_str = self.next()

        def gobble():
            nonlocal token_str
            if self.this is None:
                raise UnexpectedEOF(make(*UNEXPECTED(token_str)))
            token_str += self.next()

        if token_str is None:
            return make(*EOF)

        if token_str == NEWLINE.s:
            self.incline()
            return make(*NEWLINE)

        if token_str == quote:
            while True:
                char = self.this
                if char == newline:
                    gobble()
                    return make(*UNEXPECTED(token_str))
                elif char == esc:
                    gobble()
                    gobble()
                elif char == quote:
                    gobble()
                    return make(*STRING(token_str))
                else:
                    gobble()

        if token_str == backtick or (token_str == bracer and self.template_depth):
            dollar, brace = dollarbrace
            if token_str == backtick:
                self.template_depth += 1
            while True:
                char = self.this
                if char == esc:
                    gobble()
                    gobble()
                elif char == dollar:
                    gobble()
                    if self.this == brace:
                        gobble()
                        return make(*TEMPLATE(token_str))
                elif char == backtick:
                    self.template_depth -= 1
                    gobble()
                    return make(*TEMPLATE(token_str))
                elif char == newline:
                    self.incline()
                    gobble()
                else:
                    gobble()

        if token_str in punctuation_tree:
            tree = punctuation_tree[token_str]
            while self.this in tree:
                gobble()
            if token_str not in punctuation_map:
                return make(*UNEXPECTED(token_str))
            return make(*punctuation_map[token_str])

        if token_str in number_begin:
            seen_decimal_point = False
            while self.this in number_all:
                digit = self.next()
                if digit == dot:
                    if seen_decimal_point:
                        token_str += digit
                        return make(*UNEXPECTED(token_str))
                    seen_decimal_point= True
                token_str += digit
            return make(*NUMBER(token_str))

        if token_str in var_begin:
            while self.this in var_all:
                gobble()
            return make(*keyword_map.get(token_str, VAR(token_str)))

        return make(*UNEXPECTED(token_str))

    def __next__(self) -> Token:
        try:
            peek = self.read()
        except UnexpectedEOF as e:
            return e.token
        if peek.name == EOF.name:
            # rewind
            self.pos -= 1
            self.linepos -= 1
            self.lineno -= 1
            raise StopIteration
        return peek

    def __iter__(self) -> Iterator[Token]:
        return self
