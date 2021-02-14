from pathlib import Path
from textwrap import dedent
from unittest.mock import ANY

from dnjs import tokeniser as t
import pytest

def l(s: str):
    vs = []
    token_stream = t.TokenStream.from_source(source=s)
    while True:
        token, _ = token_stream.current, token_stream.advance()
        if token.type == t.eof:
            break
        vs.append((token.type, token.value))
    return vs

def test_empty():
    assert l(" ") == []
    assert l("") == []

def test_unexpected():
    assert l("±") == [(t.unexpected, "±")]

def test_number():
    assert l("1") == [(t.number, "1")]
    assert l(" -1.5 ") == [(t.number, "-1.5")]
    assert l(" -1..5 ") == [(t.unexpected, "-1.."), (t.number, "5")]

def test_punctuation():
    assert l(". ") == [(".", ".")]
    assert l(".") == [(".", ".")]
    assert l("...") == [("...", "...")]
    assert l("===") == [("===", "===")]
    assert l("=>.") == [("=>", "=>"), (".", ".")]
    assert l("=>.") == [("=>", "=>"), (".", ".")]
    assert l("..") == [(t.unexpected, "..")]
    assert l("....") == [("...", "..."), (".", ".")]
    assert l("..=>") == [(t.unexpected, ".."), ("=>", "=>")]


def test_var_and_keyword():
    assert l("import") == [("import", "import")]
    assert l("importfoo") == [(t.name, "importfoo")]
    assert l("from _bar const") == [("from", "from"), (t.name, "_bar"), ("const", "const")]


def test_string():
    assert l('"foo"') == [(t.string, '"foo"')]
    assert l(r'"foo\"bar"') == [(t.string, '"foo\"bar"')]
    assert l(r'"foo\\" 42') == [(t.string, '"foo\\"'), (t.number, "42")]
    assert l('42"foo') == [(t.number, "42"), (t.unexpected, '"foo')]
    assert l('"foo\nbar"') == [(t.unexpected, '"foo\n'), (t.name, 'bar'), ('unexpected', '"')]


def test_template():
    assert l('``') == [("`", "``")]
    assert l('`foo`') == [("`", "`foo`")]
    assert l(r'`foo\`bar`') == [("`", "`foo`bar`")]
    assert l(r'`foo\\` 42') == [("`", "`foo\\`"), (t.number, "42")]
    assert l(r'`foo${42}bar`') == [("`", "`foo${"), (t.number, "42"), (t.template, r'}bar`')]
    expected = [
        ("`", "`foo${"),
        (t.name, 'a'),
        ('[', '['),
        ("`", "`inner${"),
        (t.number, '1'),
        (t.template, '}2${'),
        (t.number, '3'),
        (t.template, '}`'),
        (']', ']'),
        (t.template, '}bar`')
    ]
    assert l(r'`foo${a[`inner${1}2${3}`]}bar`') == expected
    assert l('`foo\nbar`') == [("`", "`foo\nbar`")]
    assert l('`${`${a}--${b}`}`') == [
        ('`', '`${'),
        ('`', '`${'),
        (t.name, 'a'),
        (t.template, '}--${'),
        (t.name, 'b'),
        (t.template, '}`'),
        (t.template, '}`')
    ]
    assert l("{`foo`}") == [("{", "{"), ("`", "`foo`"), ("}", "}")]


def test_line_numbers():
    reader = t.TokenStream.from_source("012  56")
    eat = lambda: [reader.current, reader.advance()][0]
    assert eat() == t.Token(t.number, "012", ANY, 0, 1, 0)
    assert eat() == t.Token(t.number, "56", ANY, 5, 1, 5)
    assert eat().type == t.eof

    reader = t.TokenStream.from_source("0\n23\n567\n")
    assert eat() == t.Token(t.number, "0", ANY, 0, 1, 0)
    assert eat() == t.Token(t.number, "23", ANY, 2, 2, 0)
    assert eat() == t.Token(t.number, "567", ANY, 5, 3, 0)
    assert eat().type == t.eof

    reader = t.TokenStream.from_source("012//56\n8\n")
    assert eat() == t.Token(t.number, "012", ANY, 0, 1, 0)
    assert eat() == t.Token(t.number, "8", ANY, 8, 2, 0)
    assert eat().type == t.eof

    reader = t.TokenStream.from_source("0\n`3\n5`\n8")
    assert eat() == t.Token(t.number, "0", ANY, 0, 1, 0)
    assert eat() == t.Token("`", "`3\n5`", ANY, 2, 2, 0)
    assert eat() == t.Token(t.number, "8", ANY, 8, 4, 0)
    assert eat().type == t.eof


def test_combined():
    assert l(".12.6") == [(".", "."), (t.number, "12.6")]


def test_escaping():
    text = (Path(__file__).parent / "data/escaping.dn.js").read_text()
    assert l(text) == [(t.string, '""baz""')]

    text = (Path(__file__).parent / "data/template.dn.js").read_text()
    assert l(text)[-1] == ("}", "}")


def test_comments():
    text = '''{
        "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
        // a comment
        //
    }'''
    expected = [
        ('{', '{'),
        (t.string, '"key"'),
        (':', ':'),
        ('[', '['),
        (t.string, '"item0"'),
        (',', ','),
        (t.string, '"not//a//comment"'),
        (',', ','),
        (t.number, '3.14'),
        (',', ','),
        (t.literal, 'true'),
        (']', ']'),
        ('}', '}'),
    ]
    assert l(text) == expected
