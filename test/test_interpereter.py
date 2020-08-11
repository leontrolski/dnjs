from pathlib import Path

from dnjs import get_default_export, get_named_export

data_dir = Path(__file__).parent / "data"


def test_parser_add_assignments_reference_and_rest():
    actual = get_default_export(data_dir / "rest.dn.js")
    expected = {
        "key": ["item0", "item1", 3.14, 42, 43, True, {"bar": [42, 43]}],
        "bar": [42, 43],
    }
    assert actual == expected


def test_imports():
    actual = get_default_export(data_dir / "thisImports.dn.js")
    expected = {"foo": ["DEFAULT", [{"A": 1}], "B"]}
    assert actual == expected


def test_top_level_functions():
    actual = get_named_export(data_dir / "function.dn.js", "f")
    assert actual(1, 2) == [1, 2, 42]
    actual = get_named_export(data_dir / "function.dn.js", "g")
    assert actual() == 42.0


def test_imported_functions():
    actual = get_default_export(data_dir / "functionCall.dn.js")
    expected = {"hello": 42}
    assert actual == expected


def test_ternary_eq():
    actual = get_named_export(data_dir / "ternary.dn.js", "t")
    assert actual is "t"
    actual = get_named_export(data_dir / "ternary.dn.js", "f")
    assert actual is "f"


def test_map():
    actual = get_named_export(data_dir / "map.dn.js", "a")
    assert actual == [
        {"myI": 0.0, "myV": 1.0},
        {"myI": 1.0, "myV": 2.0},
        {"myI": 3.0, "myV": 200.0},
    ]
    actual = get_named_export(data_dir / "map.dn.js", "b")
    assert actual == [
        {"i": 0.0, "k": "1", "v": 2.0},
        {"i": 1.0, "k": "3", "v": 4.0},
    ]
    actual = get_named_export(data_dir / "map.dn.js", "c")
    assert actual == {"5": 6.0, "7": 8.0}


def test_nodes():
    actual = get_named_export(data_dir / "node.dn.js", "a")
    assert actual == {
        "attrs": {"className": ""},
        "children": [],
        "tag": "br",
    }
    actual = get_named_export(data_dir / "node.dn.js", "b")
    assert actual == {
        "tag": "div",
        "attrs": {"className": "foo bar baz", "id": "rarr"},
        "children": [
            {
                "tag": "ul",
                "attrs": {"className": "", "id": "qux"},
                "children": [
                    {"tag": "li", "attrs": {"className": ""}, "children": ["0"]},
                    {"tag": "li", "attrs": {"className": ""}, "children": ["1"]},
                    {"tag": "li", "attrs": {"className": ""}, "children": ["2"]},
                ],
            },
            "apple",
            {"tag": "br", "attrs": {"className": ""}, "children": []},
        ],
    }


def test_templates():
    actual = get_named_export(data_dir / "template.dn.js", "a")
    assert actual == "foo"
    actual = get_named_export(data_dir / "template.dn.js", "b")
    assert actual == "hello oli,\nyou are 29"
    actual = get_named_export(data_dir / "template.dn.js", "c")
    assert actual == {"foo": "\"hullo\"\ncat foo.txt > bar\ntail /dev/null", "bar": "\"baz\""}
