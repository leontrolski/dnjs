from  textwrap import dedent
from dnjs import tokeniser as t
import pytest

def l(s: str):
    return [(token.name, token.s) for token in t.Reader(s)]

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
    assert l('42"foo') == [t.NUMBER("42"), t.UNEXPECTED('"foo\n')]
    assert l('"foo\nbar"') == [t.UNEXPECTED('"foo\n'), t.VAR('bar'), t.UNEXPECTED('"\n')]


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
    reader = t.Reader("123  67")
    assert next(reader) == t.Token(*t.NUMBER("123"), 0, 1, 0)
    assert next(reader) == t.Token(*t.NUMBER("67"), 5, 1, 5)
    with pytest.raises(StopIteration):
        next(reader)

    reader = t.Reader("1\n34\n678\n")
    assert next(reader) == t.Token(*t.NUMBER("1"), 0, 1, 0)
    assert next(reader) == t.Token(*t.NUMBER("34"), 2, 2, 0)
    assert next(reader) == t.Token(*t.NUMBER("678"), 5, 3, 0)
    with pytest.raises(StopIteration):
        next(reader)

    reader = t.Reader("123//67\n9\n")
    assert next(reader) == t.Token(*t.NUMBER("123"), 0, 1, 0)
    assert next(reader) == t.Token(*t.NUMBER("9"), 8, 2, 0)
    with pytest.raises(StopIteration):
        next(reader)

def test_combined():
    assert l(".12.6") == [t.DOT, t.NUMBER("12.6")]
