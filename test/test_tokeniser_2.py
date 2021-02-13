from pathlib import Path
from textwrap import dedent
from dnjs import tokeniser_2 as t
import pytest

def l(s: str, include_newlines: bool = False):
    vs = []
    token_stream = t.TokenStream(s)
    while True:
        token = token_stream.advance(include_newlines=include_newlines)
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
    assert l("1") == [(t.literal, "1")]
    assert l(" -1.5 ") == [(t.literal, "-1.5")]
    assert l(" -1..5 ") == [(t.unexpected, "-1.."), (t.literal, "5")]

def test_punctuation():
    assert l(". ") == [(t.punctuation, ".")]
    assert l(".") == [(t.punctuation, ".")]
    assert l("...") == [(t.punctuation, "...")]
    assert l("=>.") == [(t.punctuation, "=>"), (t.punctuation, ".")]
    assert l("=>.") == [(t.punctuation, "=>"), (t.punctuation, ".")]
    assert l("..") == [(t.unexpected, "..")]
    assert l("....") == [(t.unexpected, "....")]
    assert l("..=>") == [(t.unexpected, ".."), (t.punctuation, "=>")]
    assert l("{`foo`}") == [(t.punctuation, "{"), (t.template, "`foo`"), (t.punctuation, "}")]


def test_var_and_keyword():
    assert l("import") == [(t.keyword, "import")]
    assert l("importfoo") == [(t.name, "importfoo")]
    assert l("from _bar const") == [(t.keyword, "from"), (t.name, "_bar"), (t.keyword, "const")]


def test_string():
    assert l('"foo"') == [(t.literal, '"foo"')]
    assert l(r'"foo\"bar"') == [(t.literal, r'"foo\"bar"')]
    assert l(r'"foo\\" 42') == [(t.literal, r'"foo\\"'), (t.literal, "42")]
    assert l('42"foo', include_newlines=True) == [(t.literal, "42"), (t.unexpected, '"foo\n')]
    assert l('"foo\nbar"', include_newlines=True) == [(t.unexpected, '"foo\n'), (t.name, 'bar'), (t.unexpected, '"\n')]


def test_template():
    assert l('`foo`') == [(t.template, '`foo`')]
    assert l(r'`foo\`bar`') == [(t.template, r'`foo\`bar`')]
    assert l(r'`foo\\` 42') == [(t.template, r'`foo\\`'), (t.literal, "42")]
    assert l(r'`foo${42}bar`') == [(t.template, r'`foo${'), (t.literal, "42"), (t.template, r'}bar`')]
    expected = [
        ('template', '`foo${'),
        ('name', 'a'),
        ('punctuation', '['),
        ('template', '`inner`'),
        ('punctuation', ']'),
        ('template', '}bar`')
    ]
    assert l(r'`foo${a[`inner`]}bar`') == expected
    assert l('`foo\nbar`') == [(t.template, '`foo\nbar`')]

def test_line_numbers():
    reader = t.TokenStream("012  56")
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "012"), 0, 1, 0)
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "56"), 5, 1, 5)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True).type == t.eof
    with pytest.raises(t.TokenStreamEmptyError):
        reader.advance().type

    reader = t.TokenStream("0\n23\n567\n")
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "0"), 0, 1, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "23"), 2, 2, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "567"), 5, 3, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True).type == t.eof

    reader = t.TokenStream("012//56\n8\n")
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "012"), 0, 1, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "8"), 8, 2, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True).type == t.eof

    reader = t.TokenStream("0\n`3\n5`\n8")
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "0"), 0, 1, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True)  == t.Token(*(t.template, "`3\n5`"), 2, 2, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True) == t.Token(*(t.literal, "8"), 8, 4, 0)
    assert reader.advance(include_newlines=True).type == t.newline
    assert reader.advance(include_newlines=True).type == t.eof


def test_line_numbers_no_newlines():
    reader = t.TokenStream("012  56")
    assert reader.advance() == t.Token(*(t.literal, "012"), 0, 1, 0)
    assert reader.advance() == t.Token(*(t.literal, "56"), 5, 1, 5)
    assert reader.advance().type == t.eof
    with pytest.raises(t.TokenStreamEmptyError):
        reader.advance().type

    reader = t.TokenStream("0\n23\n567\n")
    assert reader.advance() == t.Token(*(t.literal, "0"), 0, 1, 0)
    assert reader.advance() == t.Token(*(t.literal, "23"), 2, 2, 0)
    assert reader.advance() == t.Token(*(t.literal, "567"), 5, 3, 0)
    assert reader.advance().type == t.eof

    reader = t.TokenStream("012//56\n8\n")
    assert reader.advance() == t.Token(*(t.literal, "012"), 0, 1, 0)
    assert reader.advance() == t.Token(*(t.literal, "8"), 8, 2, 0)
    assert reader.advance().type == t.eof

    reader = t.TokenStream("0\n`3\n5`\n8")
    assert reader.advance() == t.Token(*(t.literal, "0"), 0, 1, 0)
    assert reader.advance()  == t.Token(*(t.template, "`3\n5`"), 2, 2, 0)
    assert reader.advance() == t.Token(*(t.literal, "8"), 8, 4, 0)
    assert reader.advance().type == t.eof

def test_combined():
    assert l(".12.6") == [(t.punctuation, "."), (t.literal, "12.6")]


def test_escaping():
    text = (Path(__file__).parent / "data/escaping.dn.js").read_text()
    assert l(text) == [(t.literal, '"\\"baz\\""')] == [(t.literal, text[:-1])]

    text = (Path(__file__).parent / "data/template.dn.js").read_text()
    assert l(text)[-1] == (t.punctuation, "}")


def test_comments():
    text = '''{
        "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
        // a comment
        //
    }'''
    expected = [
        ('punctuation', '{'),
        ('literal', '"key"'),
        ('punctuation', ':'),
        ('punctuation', '['),
        ('literal', '"item0"'),
        ('punctuation', ','),
        ('literal', '"not//a//comment"'),
        ('punctuation', ','),
        ('literal', '3.14'),
        ('punctuation', ','),
        ('literal', 'true'),
        ('punctuation', ']'),
        ('punctuation', '}'),
    ]
    assert l(text) == expected
