from textwrap import dedent
from unittest.mock import ANY

import pytest

from dnjs import parser as p
from dnjs import tokeniser as t


def parse(s: str) -> str:
    statements = p.parse_statements(t.TokenStream.from_source(source=s))
    return "\n".join(str(s) for s in statements)


def test_empty():
    assert parse("") == ""


def test_literal_and_names():
    assert parse("1") == "1"
    assert parse("1.4") == "1.4"
    assert parse('"foo"') == '"foo"'
    assert parse('bar') == 'bar'
    assert parse('true') == 'true'


def test_infixes():
    assert parse("1 === 2") == "(=== 1 2)"
    assert parse("foo.bar") == "(. foo bar)"
    assert parse("foo.bar === 4") == "(=== (. foo bar) 4)"
    assert parse("foo.bar.baz") == "(. (. foo bar) baz)"
    assert parse("(foo.bar === baz).qux") == "(. (( (=== (. foo bar) baz)) qux)"
    assert parse("[foo.bar === baz.qux]") == "([ (=== (. foo bar) (. baz qux)))"


def test_function_call():
    assert parse("f(3, 4, 5)") == "($ f (* 3 4 5))"
    assert parse("f(3, 4, g(5, 6 === 7))") == "($ f (* 3 4 ($ g (* 5 (=== 6 7)))))"
    assert parse("f(3\n, 4, g(5, \n6 === 7),)") == "($ f (* 3 4 ($ g (* 5 (=== 6 7)))))"


def test_arrays():
    assert parse('[]') == '([)'
    text = '[1, 2, null]'
    assert parse(text) == '([ 1 2 null)'
    text = '[1, [2], null]'
    assert parse(text) == '([ 1 ([ 2) null)'
    text = '[1, 2, [3, [4, 5]], null]'
    assert parse(text) == '([ 1 2 ([ 3 ([ 4 5)) null)'


def test_object():
    assert parse('{}') == '({)'
    text = '{"foo": 2}'
    assert parse(text) == '({ (: "foo" 2))'
    text = '{foo: 2, bar: 3, ...a}'
    assert parse(text) == '({ (: foo 2) (: bar 3) (... a))'
    text = '{foo: [1, {"bar": 3}],}'
    assert parse(text) == '({ (: foo ([ 1 ({ (: "bar" 3)))))'


def test_comment():
    text = """\
        {
            "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
            // a comment
            //
        }
    """
    actual = parse(text)
    expected = '({ (: "key" ([ "item0" "not//a//comment" 3.14 true)))'
    assert actual == expected


def test_imports():
    text = """\
        import m from "mithril"

        import { base, form } from "./base.dn.js"

        {
            key: ["item0", "item1", 3.14, true],
        }
    """
    actual = parse(text)
    expected = (
        '(import (from m "mithril"))\n'
        '(import (from (d{ base form) "./base.dn.js"))\n'
        '({ (: key ([ "item0" "item1" 3.14 true)))'
    )
    assert actual == expected


def test_assignments_reference_and_rest():
    text = """
        const foo = 45
        const bar = {}
        {"key": ["item0", "item1", 3.14, ...foo, true, bar], ...foo.bar, baz: 12}
    """
    actual = parse(text)
    expected = (
        '(const (= foo 45))\n'
        '(const (= bar ({)))\n'
        '({ (: "key" ([ "item0" "item1" 3.14 (... foo) true bar)) (... (. foo bar)) (: baz 12))'
    )
    assert actual == expected


def test_export():
    text = """
        export default [6]
        export const base = 42

        {"key": ["item0", "item1", 3.14, true]}
    """
    actual = parse(text)
    expected = (
        '(export (default ([ 6)))\n'
        '(export (const (= base 42)))\n'
        '({ (: "key" ([ "item0" "item1" 3.14 true)))'
    )
    assert actual == expected


def test_functions():
    text = """
        const a = (1)
        const f = () => 42
        export default (a) => a
        export const otherF = (a, b, c) => ({"foo": [1]})
        const foo = [f(), otherF(a, b, c)]
        foo(1)(2, 3)(4)
    """
    actual = parse(text)
    expected = dedent("""
        (const (= a (( 1)))
        (const (= f (=> (d*) '42)))
        (export (default (=> (d* a) 'a)))
        (export (const (= otherF (=> (d* a b c) '(( ({ (: "foo" ([ 1))))))))
        (const (= foo ([ ($ f (*)) ($ otherF (* a b c)))))
        ($ ($ ($ foo (* 1)) (* 2 3)) (* 4))
    """).strip()
    assert actual == expected

    assert parse("const foo = (a, b) => m(c)") == "(const (= foo (=> (d* a b) '($ m (* c)))))"



def test_parser_add_ternary():
    actual = parse('(a === 3) ? "foo" : "bar"')
    assert actual == '''(? (( (=== a 3)) '"foo" '"bar")'''
    actual = parse('a === (3 ? "foo" : "bar")')
    assert actual == '''(=== a (( (? 3 '"foo" '"bar")))'''
    actual = parse('a === 3 ? "foo" : "bar"')
    assert actual == '''(? (=== a 3) '"foo" '"bar")'''
    actual = parse('''
        a
            ? b
        : c
            ? d
            : e
    ''')
    assert actual == "(? a 'b '(? c 'd 'e))"


def test_map_and_filter():
    actual = parse('const a = [4, 5, 6].map((v, i) => 42).filter((v, i) => (i === 0 ? v : null) )')
    assert actual == "(const (= a ($ (. ($ (. ([ 4 5 6) map) (* (=> (d* v i) '42))) filter) (* (=> (d* v i) '(( (? (=== i 0) 'v 'null)))))))"

    actual = parse('const a = Object.entries(foo.bar).map(([k, v], i) => v)')
    assert actual == "(const (= a ($ (. ($ (. Object entries) (* (. foo bar))) map) (* (=> (d* (d[ k v) i) 'v)))))"

    actual = parse('Object.fromEntries(a.b.map((v, i) => 42))')
    assert actual == "($ (. Object fromEntries) (* ($ (. (. a b) map) (* (=> (d* v i) '42)))))"

def test_parser_add_nodes():
    text = """
    const a = m("li", "hello")
    const a = m("li#my-li.foo.bar", "hello", [1, 2])
    m(".foo#my-li.bar")
    """
    actual = parse(text)
    expected = (
        '(const (= a ($ m (* "li" "hello"))))\n'
        '(const (= a ($ m (* "li#my-li.foo.bar" "hello" ([ 1 2)))))\n'
        '($ m (* ".foo#my-li.bar"))'
    )
    assert actual == expected


def test_templates():
    text = """
    const a = `hi`
    const a = ``
    const a = `hi ${first} and ${second} ${third} `
    const a = `  hi ${first}${second}`
    const a = `$${money.amount}.00`
    const a = `many
    ${foo}
    lin//es`
    [`foo $${money.amount}.00`]
    const b = `${`${a}--${b}`}`
    """
    actual = parse(text)
    expected = (
        '(const (= a (` `hi`)))\n'
        '(const (= a (` ``)))\n'
        '(const (= a (` `hi ${ first } and ${ second } ${ third } `)))\n'
        '(const (= a (` `  hi ${ first }${ second }`)))\n'
        '(const (= a (` `$${ (. money amount) }.00`)))\n'
        '(const (= a (` `many\n'
        '    ${ foo }\n'
        '    lin//es`)))\n'
        '([ (` `foo $${ (. money amount) }.00`))\n'
        '(const (= b (` `${ (` `${ a }--${ b }`) }`)))'
    )
    assert actual == expected


def test_errors():
    with pytest.raises(p.ParseError) as e:
        parse('{a: b: c, d}')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        token is not of type: name string
        {a: b: c, d}
        __^
    """).strip()

    with pytest.raises(p.ParseError) as e:
        parse('{a: b, c d}')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        expected ',' got 'd'
        {a: b, c d}
        _________^
    """).strip()

    with pytest.raises(p.ParseError) as e:
        parse('[a, b c]')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        expected ',' got 'c'
        [a, b c]
        ______^
    """).strip()

    with pytest.raises(p.ParseError) as e:
        assert parse('import a from "b" import c from "d"')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        expected statements to be on separate lines
        import a from "b" import c from "d"
        __________________^
    """).strip()

    with pytest.raises(p.ParseError) as e:
        assert parse('[] []')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        expected statements to be on separate lines
        [] []
        ___^
    """).strip()

    with pytest.raises(p.ParseError) as e:
        assert parse('42"foo')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        unexpected token
        42"foo
        __^
    """).strip()

    with pytest.raises(p.ParseError) as e:
        assert parse('`foo${1}bar${')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        unexpected end of input
        `foo${1}bar${
        _____________^
    """).strip()

    with pytest.raises(p.ParseError) as e:
        assert parse('[===3]')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        can't be used in prefix position
        [===3]
        _^
    """).strip()


    with pytest.raises(p.ParseError) as e:
        assert parse('foo = 5')
    assert "token is not of type" in str(e.value)

    with pytest.raises(p.ParseError) as e:
        assert parse('() => {}')
    assert "token is not of type" in str(e.value)

    with pytest.raises(p.ParseError) as e:
        assert parse('{}.foo')
    assert "token is not of type" in str(e.value)


def test_assign_ternary():
    text = "const f = a === 2 ? foo : bar"
    assert parse(text) == "(const (= f (? (=== a 2) 'foo 'bar)))"

    text = "const f = () => a === 2 ? foo : bar"
    assert parse(text) == "(const (= f (=> (d*) '(? (=== a 2) 'foo 'bar))))"

    text = "() => g(a, [f(b => a === 1)])"
    assert parse(text) == "(=> (d*) '($ g (* a ([ ($ f (* (=> (d* b) '(=== a 1))))))))"
