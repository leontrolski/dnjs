from textwrap import dedent

from dnjs.parser import (
    pre_parse,
    parse,
    Dnjs,
    Import,
    Var,
    RestVar,
    DictDestruct,
    ListDestruct,
    Dot,
    Assignment,
    ExportDefault,
    Export,
    Function,
    FunctionCall,
    TernaryEq,
    Map,
    Filter,
    DictMap,
    Template,
)


def test_parser_empty():
    text = ""
    actual = parse(text)
    expected = Dnjs([])
    assert actual == expected


def test_parser_json():
    text = '''{"key": ["item0", "item1", 3.14, true, "\\"baz\\""]}'''
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
                        string	"\\"baz\\""
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs([{"key": ["item0", "item1", 3.14, True, '\"baz\"']}])
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
                var	m
                string	"mithril"
            import_
                dict_destruct
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
            Import(DictDestruct([Var(name="base"), Var(name="form")]), "./base.dn.js"),
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
                    var	foo
                    number	45
                assignment
                    var	bar
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
            Assignment(var=Var(name="foo"), value=45),
            Assignment(var=Var(name="bar"), value={}),
            {
                RestVar(var=Var(name="foo")): None,
                "key": [
                    "item0",
                    "item1",
                    3.14,
                    RestVar(var=Var(name="foo")),
                    True,
                    Var(name="bar"),
                ],
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
                    var	base
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
        export const otherF = (a, b, c) => ({"foo": [1]})
        const foo = [f(), otherF(a, b, c)]
    """
    expected = dedent(
        """\
        dnjs
            assignment
                var	f
                function
                    number	42
            export_default
                function
                    var	a
                    var	a
            export
                assignment
                    var	otherF
                    function
                        var	a
                        var	b
                        var	c
                        dict
                            pair
                                string	"foo"
                                list
                                    number	1
            assignment
                var	foo
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
            Assignment(var=Var(name="f"), value=Function(args=[], return_value=42)),
            ExportDefault(
                value=Function(args=[Var(name="a")], return_value=Var(name="a"))
            ),
            Export(
                assignment=Assignment(
                    var=Var(name="otherF"),
                    value=Function(
                        args=[Var(name="a"), Var(name="b"), Var(name="c")],
                        return_value={"foo": [1]},
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
        const a = [4, 5, 6].map((v, i) => 42).filter((v, i) => (i === 0 ? v : null) )
        const a = Object.entries(foo.bar).map(([k, v], i) => v)
        Object.fromEntries(a.b.map((v, i) => 42))
    """
    expected = dedent(
        """\
        dnjs
            assignment
                var	a
                function_call
                    dot
                        function_call
                            dot
                                list
                                    number	4
                                    number	5
                                    number	6
                                var	map
                            function
                                var	v
                                var	i
                                number	42
                        var	filter
                    function
                        var	v
                        var	i
                        ternary_eq
                            var	i
                            number	0
                            var	v
                            null
            assignment
                var	a
                function_call
                    dot
                        function_call
                            dot
                                var	Object
                                var	entries
                            dot
                                var	foo
                                var	bar
                        var	map
                    function
                        list_destruct
                            var	k
                            var	v
                        var	i
                        var	v
            function_call
                dot
                    var	Object
                    var	fromEntries
                function_call
                    dot
                        dot
                            var	a
                            var	b
                        var	map
                    function
                        var	v
                        var	i
                        number	42
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        values=[
            Assignment(
                var=Var(name="a"),
                value=FunctionCall(
                    var=Dot(
                        left=FunctionCall(
                            var=Dot(left=[4, 5, 6], right=Var(name="map")),
                            values=[
                                Function(
                                    args=[Var(name="v"), Var(name="i")], return_value=42
                                )
                            ],
                        ),
                        right=Var(name="filter"),
                    ),
                    values=[
                        Function(
                            args=[Var(name="v"), Var(name="i")],
                            return_value=TernaryEq(
                                left=Var(name="i"),
                                right=0,
                                if_equal=Var(name="v"),
                                if_not_equal=None,
                            ),
                        )
                    ],
                ),
            ),
            Assignment(
                var=Var(name="a"),
                value=FunctionCall(
                    var=Dot(
                        left=FunctionCall(
                            var=Dot(left=Var(name="Object"), right=Var(name="entries")),
                            values=[Dot(left=Var(name="foo"), right=Var(name="bar"))],
                        ),
                        right=Var(name="map"),
                    ),
                    values=[
                        Function(
                            args=[
                                ListDestruct(vars=[Var(name="k"), Var(name="v")]),
                                Var(name="i"),
                            ],
                            return_value=Var(name="v"),
                        )
                    ],
                ),
            ),
            FunctionCall(
                var=Dot(left=Var(name="Object"), right=Var(name="fromEntries")),
                values=[
                    FunctionCall(
                        var=Dot(
                            left=Dot(left=Var(name="a"), right=Var(name="b")),
                            right=Var(name="map"),
                        ),
                        values=[
                            Function(
                                args=[Var(name="v"), Var(name="i")], return_value=42
                            )
                        ],
                    )
                ],
            ),
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
                var	a
                function_call
                    var	m
                    string	"li"
                    string	"hello"
            assignment
                var	a
                function_call
                    var	m
                    string	"li#my-li.foo.bar"
                    string	"hello"
                    list
                        number	1
                        number	2
            function_call
                var	m
                string	".foo#my-li.bar"
    """
    )
    tree = pre_parse(text)
    actual = tree.pretty(indent_str="    ")
    assert actual.splitlines() == expected.splitlines()

    actual = parse(text)
    expected = Dnjs(
        values=[
            Assignment(
                var=Var(name="a"),
                value=FunctionCall(var=Var(name="m"), values=["li", "hello"]),
            ),
            Assignment(
                var=Var(name="a"),
                value=FunctionCall(
                    var=Var(name="m"), values=["li#my-li.foo.bar", "hello", [1, 2]]
                ),
            ),
            FunctionCall(var=Var(name="m"), values=[".foo#my-li.bar"]),
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
        values=[
            Assignment(var=Var(name="a"), value=Template(values=["hi"])),
            Assignment(
                var=Var(name="a"),
                value=Template(
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
                var=Var(name="a"),
                value=Template(
                    values=["  hi ", Var(name="first"), "", Var(name="second"), ""]
                ),
            ),
            Assignment(
                var=Var(name="a"),
                value=Template(
                    values=[
                        "$",
                        Dot(left=Var(name="money"), right=Var(name="amount")),
                        ".00",
                    ]
                ),
            ),
            Assignment(
                var=Var(name="a"),
                value=Template(values=["many\n", Var(name="foo"), "\nlin//es"]),
            ),
            [
                Template(
                    values=[
                        "foo $",
                        Dot(left=Var(name="money"), right=Var(name="amount")),
                        ".00",
                    ]
                )
            ],
        ]
    )
    assert actual == expected
