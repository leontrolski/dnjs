from textwrap import dedent

from dnjs.parser import (
    pre_parse,
    parse,
    Dnjs,
    Import,
    Var,
    RestVar,
    Destructure,
    Assignment,
    ExportDefault,
    Export,
    Function,
    FunctionCall,
    TernaryEq,
    Map,
    Filter,
    DictMap,
    FromEntries,
    Tag,
    Class,
    Id,
    Node,
    Template,
)


def test_parser_empty():
    text = ""
    actual = parse(text)
    expected = Dnjs([])
    assert actual == expected


def test_parser_json():
    text = '{"key": ["item0", "item1", 3.14, true]}'
    expected = dedent(
        """\
        dnjs
            dict
                pair
                    string	"key"
                    list
                        string	"item0"
                        string	"item1"
                        number	3.14
                        true
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs([{"key": ["item0", "item1", 3.14, True]}])
    assert actual == expected


def test_parser_add_comments():
    text = """\
        {
            "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
            // a comment
            //
        }
    """
    expected = dedent(
        """\
        dnjs
            dict
                pair
                    string	"key"
                    list
                        string	"item0"
                        string	"not//a//comment"
                        number	3.14
                        true
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs([{"key": ["item0", "not//a//comment", 3.14, True]}])
    assert actual == expected


def test_parser_add_imports():
    text = """\
        import m from "mithril"

        import { base, form } from "./base.dn.js"

        {
            "key": ["item0", "item1", 3.14, true],
        }
    """
    expected = dedent(
        """\
        dnjs
            import_
                basic_var	m
                string	"mithril"
            import_
                destructure
                    var	base
                    var	form
                string	"./base.dn.js"
            dict
                pair
                    string	"key"
                    list
                        string	"item0"
                        string	"item1"
                        number	3.14
                        true
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            Import(Var("m"), "mithril"),
            Import(Destructure([Var(name="base"), Var(name="form")]), "./base.dn.js"),
            {"key": ["item0", "item1", 3.14, True]},
        ]
    )
    assert actual == expected


def test_parser_add_assignments_reference_and_rest():
    text = """
        const foo = 45
        const bar = {}
        {"key": ["item0", "item1", 3.14, ...foo, true, bar], ...foo}
    """
    expected = dedent(
        """\
        dnjs
            assignment
                basic_var	foo
                number	45
            assignment
                basic_var	bar
                dict
            dict
                pair
                    string	"key"
                    list
                        string	"item0"
                        string	"item1"
                        number	3.14
                        rest_var
                            var	foo
                        true
                        var	bar
                rest_var
                    var	foo
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            Assignment(var=Var("foo"), value=45.0),
            Assignment(var=Var("bar"), value={}),
            {
                "key": [
                    "item0",
                    "item1",
                    3.14,
                    RestVar(var=Var(name="foo")),
                    True,
                    Var("bar"),
                ],
                RestVar(var=Var(name="foo")): None,
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
    expected = dedent(
        """\
        dnjs
            export_default
                list
                    number	6
            export
                assignment
                    basic_var	base
                    number	42
            dict
                pair
                    string	"key"
                    list
                        string	"item0"
                        string	"item1"
                        number	3.14
                        true
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            ExportDefault([6.0]),
            Export(Assignment(var=Var(name="base"), value=42.0)),
            {"key": ["item0", "item1", 3.14, True]},
        ]
    )
    assert actual == expected


def test_parser_add_top_level_functions():
    text = """
        const f = () => 42
        export default (a) => a
        export const otherF = (a, b, c) => {"foo": [1]}
        const foo = [(f)(), (otherF)(a, b, c)]
    """
    expected = dedent(
        """\
        dnjs
            assignment
                basic_var	f
                function
                    number	42
            export_default
                function
                    basic_var	a
                    var	a
            export
                assignment
                    basic_var	otherF
                    function
                        basic_var	a
                        basic_var	b
                        basic_var	c
                        dict
                            pair
                                string	"foo"
                                list
                                    number	1
            assignment
                basic_var	foo
                list
                    function_call
                        var	f
                    function_call
                        var	otherF
                        var	a
                        var	b
                        var	c
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            Assignment(var=Var(name="f"), value=Function(args=[], return_value=42.0)),
            ExportDefault(Function(args=[Var(name="a")], return_value=Var(name="a"))),
            Export(
                Assignment(
                    var=Var(name="otherF"),
                    value=Function(
                        args=[Var(name="a"), Var(name="b"), Var(name="c")],
                        return_value={"foo": [1.0]},
                    ),
                )
            ),
            Assignment(
                var=Var(name="foo"),
                value=[
                    FunctionCall(var=Var(name="f"), values=[]),
                    FunctionCall(
                        var=Var(name="otherF"),
                        values=[Var(name="a"), Var(name="b"), Var(name="c")],
                    ),
                ],
            ),
        ]
    )
    assert actual == expected


def test_parser_add_ternary():
    text = '{"a": [a === 3 ? "foo" : "bar"]}'
    expected = dedent(
        """\
        dnjs
            dict
                pair
                    string	"a"
                    list
                        ternary_eq
                            var	a
                            number	3
                            string	"foo"
                            string	"bar"
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            {
                "a": [
                    TernaryEq(
                        left=Var(name="a"),
                        right=3.0,
                        if_equal="foo",
                        if_not_equal="bar",
                    )
                ]
            }
        ]
    )
    assert actual == expected


def test_parser_add_map_and_filter():
    text = """
        const a = [4, 5, 6].map((v, i) => 42).filter((v, i) => i === 0 ? v : null)
        const a = Object.entries(foo.bar).map(([k, v], i) => v)
        Object.fromEntries(a.b.map((v, i) => 42))
    """
    expected = dedent(
        """\
        dnjs
            assignment
                basic_var	a
                filter
                    map
                        list
                            number	4
                            number	5
                            number	6
                        number	42
                    ternary_eq
                        var	i
                        number	0
                        var	v
                        null
            assignment
                basic_var	a
                dict_map
                    var
                        foo
                        bar
                    var	v
            from_entries
                map
                    var
                        a
                        b
                    number	42
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            Assignment(
                Var("a"),
                Filter(
                    Map([4.0, 5.0, 6.0], 42.0),
                    TernaryEq(
                        left=Var(name="i"),
                        right=0.0,
                        if_equal=Var(name="v"),
                        if_not_equal=None,
                    ),
                ),
            ),
            Assignment(Var("a"), DictMap(Var(name="foo.bar"), Var(name="v"))),
            FromEntries(Map(Var(name="a.b"), 42.0)),
        ]
    )
    assert actual == expected


def test_parser_add_nodes():
    text = """
    const a = m("li", "hello")
    const a = m("li#my-li.foo.bar", "hello", [1, 2])
    m(".foo#my-li.bar")
    """
    expected = dedent(
        """\
        dnjs
            assignment
                basic_var	a
                node
                    node_properties
                        tag	li
                    string	"hello"
            assignment
                basic_var	a
                node
                    node_properties
                        tag	li
                        id	my-li
                        class_	foo
                        class_	bar
                    string	"hello"
                    list
                        number	1
                        number	2
            node
                node_properties
                    class_	foo
                    id	my-li
                    class_	bar
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            Assignment(Var("a"), Node(properties=[Tag("li")], values=["hello"])),
            Assignment(
                Var("a"),
                Node(
                    properties=[Tag("li"), Id("my-li"), Class("foo"), Class("bar")],
                    values=["hello", [1.0, 2.0]],
                ),
            ),
            Node(properties=[Class("foo"), Id("my-li"), Class("bar")], values=[]),
        ]
    )
    assert actual == expected


def test_parser_add_template():
    text = dedent(
        """
    const a = `hi`
    const a = `hi ${first} and ${second} ${third} `
    const a = `  hi ${first}${second}`
    const a = `$${money.amount}.00`
    const a = `many
    ${foo}
    lin//es`
    [`foo $${money.amount}.00`]
    """
    )
    expected = dedent(
        """

    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    # assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        [
            Assignment(Var("a"), Template(values=["hi"])),
            Assignment(
                Var("a"),
                Template(
                    values=[
                        "hi ",
                        Var(name="first"),
                        " and ",
                        Var(name="second"),
                        " ",
                        Var(name="third"),
                        " ",
                    ]
                ),
            ),
            Assignment(
                Var("a"),
                Template(
                    values=["  hi ", Var(name="first"), "", Var(name="second"), ""]
                ),
            ),
            Assignment(
                Var("a"), Template(values=["$", Var(name="money.amount"), ".00"])
            ),
            Assignment(
                var=Var(name="a"),
                value=Template(values=["many\n", Var(name="foo"), "\nlin//es"]),
            ),
            [Template(values=["foo $", Var(name="money.amount"), ".00"])],
        ]
    )
    assert actual == expected
