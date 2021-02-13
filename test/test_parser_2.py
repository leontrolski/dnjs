from dnjs import parser_2 as p

def parse(s: str) -> str:
    return repr(p.parse(p.rule_map, p.TokenStream(s)))


def test_foo():
    assert parse("1") == "1"
