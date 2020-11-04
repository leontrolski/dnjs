from pathlib import Path
from textwrap import dedent
from dnjs import tokeniser as t
import pytest

def l(s: str, strip_final_newline: bool = True):
    tokens = [(token.name, token.s) for token in t.Reader(s)]
    return tokens[:-1] if strip_final_newline else tokens

def test_empty():
    assert l(" ") == []
    assert l("") == []

def test_unexpected():
    assert l("±") == [t.UNEXPECTED("±")]

def test_number():
    assert l(" -1.5 ") == [t.NUMBER("-1.5")]
    assert l(" -1..5 ") == [t.UNEXPECTED("-1.."), t.NUMBER("5")]

def test_punctuation():
    assert l(". ") == [t.DOT]
    assert l(".") == [t.DOT]
    assert l("...") == [t.ELLIPSIS]
    assert l("=>.") == [t.ARROW, t.DOT]
    assert l("=>.") == [t.ARROW, t.DOT]
    assert l("..") == [t.UNEXPECTED("..")]
    assert l("....") == [t.UNEXPECTED("....")]
    assert l("..=>") == [t.UNEXPECTED(".."), t.ARROW]
    assert l("{`foo`}") == [t.BRACEL, t.TEMPLATE("`foo`"), t.BRACER]


def test_var_and_keyword():
    assert l("import") == [t.IMPORT]
    assert l("importfoo") == [t.VAR("importfoo")]
    assert l("from _bar const") == [t.FROM, t.VAR("_bar"), t.CONST]


def test_string():
    assert l('"foo"') == [t.STRING('"foo"')]
    assert l(r'"foo\"bar"') == [t.STRING(r'"foo\"bar"')]
    assert l(r'"foo\\" 42') == [t.STRING(r'"foo\\"'), t.NUMBER("42")]
    assert l('42"foo', strip_final_newline=False) == [t.NUMBER("42"), t.UNEXPECTED('"foo\n')]
    assert l('"foo\nbar"', strip_final_newline=False) == [t.UNEXPECTED('"foo\n'), t.VAR('bar'), t.UNEXPECTED('"\n')]


def test_template():
    assert l('`foo`') == [t.TEMPLATE('`foo`')]
    assert l(r'`foo\`bar`') == [t.TEMPLATE(r'`foo\`bar`')]
    assert l(r'`foo\\` 42') == [t.TEMPLATE(r'`foo\\`'), t.NUMBER("42")]
    assert l(r'`foo${42}bar`') == [t.TEMPLATE(r'`foo${'), t.NUMBER("42"), t.TEMPLATE(r'}bar`')]
    expected = [
        ('TEMPLATE', '`foo${'),
        ('VAR', 'a'),
        ('BRACKL', '['),
        ('TEMPLATE', '`inner`'),
        ('BRACKR', ']'),
        ('TEMPLATE', '}bar`')
    ]
    assert l(r'`foo${a[`inner`]}bar`') == expected
    assert l('`foo\nbar`') == [t.TEMPLATE('`foo\nbar`')]

def test_line_numbers():
    # note that at the end of iteration, the reader's pos is 1 char ahead of the end
    reader = t.Reader("012  56")
    assert next(reader) == t.Token(*t.NUMBER("012"), 0, 1, 0)
    assert next(reader) == t.Token(*t.NUMBER("56"), 5, 1, 5)
    assert next(reader).name == t.NEWLINE.name
    with pytest.raises(StopIteration):
        next(reader)

    reader = t.Reader("0\n23\n567\n")
    assert next(reader) == t.Token(*t.NUMBER("0"), 0, 1, 0)
    assert next(reader).name == t.NEWLINE.name
    assert next(reader) == t.Token(*t.NUMBER("23"), 2, 2, 0)
    assert next(reader).name == t.NEWLINE.name
    assert next(reader) == t.Token(*t.NUMBER("567"), 5, 3, 0)
    assert next(reader).name == t.NEWLINE.name
    with pytest.raises(StopIteration):
        next(reader)

    reader = t.Reader("012//56\n8\n")
    assert next(reader) == t.Token(*t.NUMBER("012"), 0, 1, 0)
    assert next(reader).name == t.NEWLINE.name
    assert next(reader) == t.Token(*t.NUMBER("8"), 8, 2, 0)
    assert next(reader).name == t.NEWLINE.name
    with pytest.raises(StopIteration):
        next(reader)

    reader = t.Reader("0\n`3\n5`\n8")
    assert next(reader) == t.Token(*t.NUMBER("0"), 0, 1, 0)
    assert next(reader).name == t.NEWLINE.name
    assert next(reader)  == t.Token(*t.TEMPLATE("`3\n5`"), 2, 2, 0)
    assert next(reader).name == t.NEWLINE.name
    assert next(reader) == t.Token(*t.NUMBER("8"), 8, 4, 0)
    assert next(reader).name == t.NEWLINE.name
    with pytest.raises(StopIteration):
        next(reader)

def test_combined():
    assert l(".12.6") == [t.DOT, t.NUMBER("12.6")]


def test_escaping():
    text = (Path(__file__).parent / "data/escaping.dn.js").read_text()
    assert l(text) == [t.STRING('"\\"baz\\""')] == [t.STRING(text[:-1])]

    text = (Path(__file__).parent / "data/template.dn.js").read_text()
    assert l(text)[-1] == t.BRACER


def test_comments():
    text = '''{
        "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
        // a comment
        //
    }'''
    expected = [
        ('BRACEL', '{'),
        ('NEWLINE', '\n'),
        ('STRING', '"key"'),
        ('COLON', ':'),
        ('BRACKL', '['),
        ('STRING', '"item0"'),
        ('COMMA', ','),
        ('STRING', '"not//a//comment"'),
        ('COMMA', ','),
        ('NUMBER', '3.14'),
        ('COMMA', ','),
        ('TRUE', 'true'),
        ('BRACKR', ']'),
        ('NEWLINE', '\n'),
        ('NEWLINE', '\n'),
        ('NEWLINE', '\n'),
        ('BRACER', '}'),
    ]
    assert l(text) == expected
