from textwrap import dedent

import pytest

from dnjs.parser2 import (
    parse,
    Dnjs,
    ParserError,
    Import,
    Var,
    RestVar,
    DictDestruct,
    Dot,
    Assignment,
    ExportDefault,
    Export,
    Function,
    FunctionCall,
    # TernaryEq,
    # Map,
    # Filter,
    # DictMap,
    Template,
)

# def p(s: str) -> str:
#     return [l.strip() for l in s.splitlines() if l.strip()]


def test_parser_empty():
    text = ""
    actual = parse(text)
    expected = Dnjs([])
    assert actual == expected


def test_unknown_token():
    with pytest.raises(ParserError) as e:
        parse('"foo')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        Not sure how to deal with UNEXPECTED token: "foo

        "foo
        ^
    """).strip()


def test_parse_atoms():
    assert parse('"foo"') == Dnjs(["foo"])
    assert parse('"foo"\n"bar"') == Dnjs(["foo", "bar"])
    assert parse('"foo\\nbär"') == Dnjs(["foo\nbär"])
    assert parse('23') == Dnjs([23])
    assert parse('-34.8') == Dnjs([-34.8])
    assert parse('true') == Dnjs([True])
    assert parse('false') == Dnjs([False])
    assert parse('null') == Dnjs([None])

def test_parse_array():
    assert parse('[]') == Dnjs([[]])
    text = '[1, 2, null]'
    assert parse(text) == Dnjs([[1, 2, None]])
    text = '[1, [2], null]'
    assert parse(text) == Dnjs([[1, [2], None]])
    text = '[1, 2, [3, [4, 5]], null]'
    assert parse(text) == Dnjs([[1, 2, [3, [4, 5]], None]])
    with pytest.raises(ParserError) as e:
        parse('[1,,]')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        Array, didn't expect a comma here
        [1,,]
           ^
    """).strip()
    with pytest.raises(ParserError) as e:
        parse('[1 2]')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        Array, expected a comma here
        [1 2]
           ^
    """).strip()

def test_parse_object():
    assert parse('{}') == Dnjs([{}])
    text = '{"foo": 2}'
    assert parse(text) == Dnjs([{"foo": 2}])
    text = '{foo: 2}'
    assert parse(text) == Dnjs([{"foo": 2}])
    text = '{foo: [1, {"bar": 3}],}'
    assert parse(text) == Dnjs([{"foo": [1, {"bar": 3}]}])
    with pytest.raises(ParserError) as e:
        parse('{foo}')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        Object's key needs a value
        {foo}
            ^
    """).strip()
    with pytest.raises(ParserError) as e:
        parse('{foo, "are"}')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        Object, expected a colon here
        {foo, "are"}
            ^
    """).strip()
    with pytest.raises(ParserError) as e:
        parse('{foo:1, 2: 3}')
    assert str(e.value) == dedent("""
        <ParserError line:1>
        Object, expected a string here
        {foo:1, 2: 3}
                ^
    """).strip()
    # TODO: complete error coverage


def test_parser_add_comments():
    text = """\
        {
            "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
            // a comment
            //
        }
    """
    actual = parse(text)
    expected = Dnjs([{"key": ["item0", "not//a//comment", 3.14, True]}])
    assert actual == expected


def test_parser_add_imports():
    text = """\
        import m from "mithril"

        import { base, form } from "./base.dn.js"

        {
            key: ["item0", "item1", 3.14, true],
        }
    """
    actual = parse(text)
    expected = Dnjs(
        [
            Import(Var("m"), "mithril"),
            Import(DictDestruct([Var(name="base"), Var(name="form")]), "./base.dn.js"),
            {"key": ["item0", "item1", 3.14, True]},
        ]
    )
    assert actual == expected


def test_parser_add_assignments_reference_and_rest():
    text = """
        const foo = 45
        const bar = {}
        {"key": ["item0", "item1", 3.14, ...foo, true, bar], ...foo, baz: 12}
    """
    actual = parse(text)
    expected = Dnjs(
        [
            Assignment(var=Var(name="foo"), value=45),
            Assignment(var=Var(name="bar"), value={}),
            {
                "key": [
                    "item0",
                    "item1",
                    3.14,
                    RestVar(var=Var(name="foo")),
                    True,
                    Var(name="bar"),
                ],
                RestVar(var=Var(name="foo")): None,
                "baz": 12,
            },
        ]
    )
    assert actual == expected


def test_parser_add_export():
    text = """
        export default [6]
        export const base = 42

        {"key": ["item0", "item1", 3.14, true]}
    """
    actual = parse(text)
    expected = Dnjs(
        [
            ExportDefault([6.0]),
            Export(Assignment(var=Var(name="base"), value=42.0)),
            {"key": ["item0", "item1", 3.14, True]},
        ]
    )
    assert actual == expected

def test_parser_add_dot():
    text = """
        const foo = {bar: 42}
        foo.bar
        foo.bar.qux
    """
    actual = parse(text)
    expected = Dnjs(
        [
            Assignment(var=Var(name="foo"), value={"bar": 42}),
            Dot(left=Var(name="foo"), right="bar"),
            Dot(left=Dot(left=Var(name="foo"), right="bar"), right="qux"),
        ]
    )
    assert actual == expected


# def test_parser_add_top_level_functions():
#     text = """
#         const a = (1)
#         const f = () => 42
#         export default (a) => a
#         export const otherF = (a, b, c) => ({"foo": [1]})
#         const foo = [f(), otherF(a, b, c)]
#     """
#     actual = parse(text)
#     expected = Dnjs(
#         [
#             Assignment(var=Var(name="a"), value=1),
#             Assignment(var=Var(name="f"), value=Function(args=[], return_value=42)),
#             ExportDefault(
#                 value=Function(args=[Var(name="a")], return_value=Var(name="a"))
#             ),
#             Export(
#                 assignment=Assignment(
#                     var=Var(name="otherF"),
#                     value=Function(
#                         args=[Var(name="a"), Var(name="b"), Var(name="c")],
#                         return_value={"foo": [1]},
#                     ),
#                 )
#             ),
#             Assignment(
#                 var=Var(name="foo"),
#                 value=[
#                     FunctionCall(var=Var(name="f"), values=[]),
#                     FunctionCall(
#                         var=Var(name="otherF"),
#                         values=[Var(name="a"), Var(name="b"), Var(name="c")],
#                     ),
#                 ],
#             ),
#         ]
#     )
#     assert actual == expected


# def test_parser_add_ternary():
#     text = '{"a": [a === 3 ? "foo" : "bar"]}'
#     expected = dedent(
#         """\
#         dnjs
#             dict
#                 pair
#                     string	"a"
#                     list
#                         ternary_eq
#                             var	a
#                             number	3
#                             string	"foo"
#                             string	"bar"
#     """
#     )
#     tree = pre_parse(text)
#     actual = tree.pretty(indent_str="    ")
#     assert p(actual) == p(expected)

#     actual = parse(text)
#     expected = Dnjs(
#         [
#             {
#                 "a": [
#                     TernaryEq(
#                         left=Var(name="a"),
#                         right=3.0,
#                         if_equal="foo",
#                         if_not_equal="bar",
#                     )
#                 ]
#             }
#         ]
#     )
#     assert actual == expected


# def test_parser_add_map_and_filter():
#     text = """
#         const a = [4, 5, 6].map((v, i) => 42).filter((v, i) => (i === 0 ? v : null) )
#         const a = Object.entries(foo.bar).map(([k, v], i) => v)
#         Object.fromEntries(a.b.map((v, i) => 42))
#     """
#     expected = dedent(
#         """\
#         dnjs
#             assignment
#                 var	a
#                 function_call
#                     dot
#                         function_call
#                             dot
#                                 list
#                                     number	4
#                                     number	5
#                                     number	6
#                                 var	map
#                             function
#                                 var	v
#                                 var	i
#                                 number	42
#                         var	filter
#                     function
#                         var	v
#                         var	i
#                         ternary_eq
#                             var	i
#                             number	0
#                             var	v
#                             null
#             assignment
#                 var	a
#                 function_call
#                     dot
#                         function_call
#                             dot
#                                 var	Object
#                                 var	entries
#                             dot
#                                 var	foo
#                                 var	bar
#                         var	map
#                     function
#                         list
#                             var	k
#                             var	v
#                         var	i
#                         var	v
#             function_call
#                 dot
#                     var	Object
#                     var	fromEntries
#                 function_call
#                     dot
#                         dot
#                             var	a
#                             var	b
#                         var	map
#                     function
#                         var	v
#                         var	i
#                         number	42
#     """
#     )
#     tree = pre_parse(text)
#     actual = tree.pretty(indent_str="    ")
#     assert p(actual) == p(expected)

#     actual = parse(text)
#     expected = Dnjs(
#         values=[
#             Assignment(
#                 var=Var(name="a"),
#                 value=FunctionCall(
#                     var=Dot(
#                         left=FunctionCall(
#                             var=Dot(left=[4, 5, 6], right=Var(name="map")),
#                             values=[
#                                 Function(
#                                     args=[Var(name="v"), Var(name="i")], return_value=42
#                                 )
#                             ],
#                         ),
#                         right=Var(name="filter"),
#                     ),
#                     values=[
#                         Function(
#                             args=[Var(name="v"), Var(name="i")],
#                             return_value=TernaryEq(
#                                 left=Var(name="i"),
#                                 right=0,
#                                 if_equal=Var(name="v"),
#                                 if_not_equal=None,
#                             ),
#                         )
#                     ],
#                 ),
#             ),
#             Assignment(
#                 var=Var(name="a"),
#                 value=FunctionCall(
#                     var=Dot(
#                         left=FunctionCall(
#                             var=Dot(left=Var(name="Object"), right=Var(name="entries")),
#                             values=[Dot(left=Var(name="foo"), right=Var(name="bar"))],
#                         ),
#                         right=Var(name="map"),
#                     ),
#                     values=[
#                         Function(
#                             args=[
#                                 [Var(name="k"), Var(name="v")],
#                                 Var(name="i"),
#                             ],
#                             return_value=Var(name="v"),
#                         )
#                     ],
#                 ),
#             ),
#             FunctionCall(
#                 var=Dot(left=Var(name="Object"), right=Var(name="fromEntries")),
#                 values=[
#                     FunctionCall(
#                         var=Dot(
#                             left=Dot(left=Var(name="a"), right=Var(name="b")),
#                             right=Var(name="map"),
#                         ),
#                         values=[
#                             Function(
#                                 args=[Var(name="v"), Var(name="i")], return_value=42
#                             )
#                         ],
#                     )
#                 ],
#             ),
#         ]
#     )
#     assert actual == expected


# def test_parser_add_nodes():
#     text = """
#     const a = m("li", "hello")
#     const a = m("li#my-li.foo.bar", "hello", [1, 2])
#     m(".foo#my-li.bar")
#     """
#     expected = dedent(
#         """\
#         dnjs
#             assignment
#                 var	a
#                 function_call
#                     var	m
#                     string	"li"
#                     string	"hello"
#             assignment
#                 var	a
#                 function_call
#                     var	m
#                     string	"li#my-li.foo.bar"
#                     string	"hello"
#                     list
#                         number	1
#                         number	2
#             function_call
#                 var	m
#                 string	".foo#my-li.bar"
#     """
#     )
#     tree = pre_parse(text)
#     actual = tree.pretty(indent_str="    ")
#     assert p(actual) == p(expected)

#     actual = parse(text)
#     expected = Dnjs(
#         values=[
#             Assignment(
#                 var=Var(name="a"),
#                 value=FunctionCall(var=Var(name="m"), values=["li", "hello"]),
#             ),
#             Assignment(
#                 var=Var(name="a"),
#                 value=FunctionCall(
#                     var=Var(name="m"), values=["li#my-li.foo.bar", "hello", [1, 2]]
#                 ),
#             ),
#             FunctionCall(var=Var(name="m"), values=[".foo#my-li.bar"]),
#         ]
#     )
#     assert actual == expected


# def test_parser_add_template():
#     text = dedent(
#         """
#     const a = `hi`
#     const a = `hi ${first} and ${second} ${third} `
#     const a = `  hi ${first}${second}`
#     const a = `$${money.amount}.00`
#     const a = `many
#     ${foo}
#     lin//es`
#     [`foo $${money.amount}.00`]
#     """
#     )
#     expected = dedent(
#         """

#     """
#     )
#     tree = pre_parse(text)
#     actual = tree.pretty(indent_str="    ")
#     # assert p(actual) == p(expected)

#     actual = parse(text)
#     expected = Dnjs(
#         values=[
#             Assignment(var=Var(name="a"), value=Template(values=["hi"])),
#             Assignment(
#                 var=Var(name="a"),
#                 value=Template(
#                     values=[
#                         "hi ",
#                         Var(name="first"),
#                         " and ",
#                         Var(name="second"),
#                         " ",
#                         Var(name="third"),
#                         " ",
#                     ]
#                 ),
#             ),
#             Assignment(
#                 var=Var(name="a"),
#                 value=Template(
#                     values=["  hi ", Var(name="first"), "", Var(name="second"), ""]
#                 ),
#             ),
#             Assignment(
#                 var=Var(name="a"),
#                 value=Template(
#                     values=[
#                         "$",
#                         Dot(left=Var(name="money"), right=Var(name="amount")),
#                         ".00",
#                     ]
#                 ),
#             ),
#             Assignment(
#                 var=Var(name="a"),
#                 value=Template(values=["many\n", Var(name="foo"), "\nlin//es"]),
#             ),
#             [
#                 Template(
#                     values=[
#                         "foo $",
#                         Dot(left=Var(name="money"), right=Var(name="amount")),
#                         ".00",
#                     ]
#                 )
#             ],
#         ]
#     )
#     assert actual == expected
