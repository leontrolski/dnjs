from pathlib import Path
from textwrap import dedent
from typing import Union

import pytest

from dnjs import interpreter
from dnjs import parser as p
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
        {"myI": 0, "myV": 1},
        {"myI": 1, "myV": 2},
        {"myI": 3, "myV": 200},
    ]
    actual = get_named_export(data_dir / "map.dn.js", "b")
    assert actual == [
        {"i": 0, "k": "3", "v": 4},
    ]
    actual = get_named_export(data_dir / "map.dn.js", "c")
    assert actual == {"5": 6, "7": 8}

    actual = get_named_export(data_dir / "map.dn.js", "d")
    assert actual == True

    actual = get_named_export(data_dir / "map.dn.js", "e")
    assert actual == False


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


def test_rest_error():
    with pytest.raises(p.ParseError) as e:
        get_default_export(data_dir / "errors/rest.dn.js")
    assert str(e.value).splitlines()[1:] == dedent("""
        must be of type: {
            ...foo,
        _______^
    """).strip().splitlines()


def test_scope_error():
    with pytest.raises(p.ParseError) as e:
        get_default_export(data_dir / "errors/scope.dn.js")
    assert str(e.value).splitlines()[1:] == dedent("""
        variable bar is not in scope
        export default bar
        _______________^
    """).strip().splitlines()
