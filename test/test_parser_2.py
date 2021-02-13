from dnjs import parser_2 as p

def parse(s: str) -> str:
    token_stream = p.TokenStream(s)
    return repr(p.parse(p.rule_map, token_stream))


def test_foo():
    assert parse("1") == "1"
