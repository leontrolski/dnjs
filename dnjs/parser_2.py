from dnjs.helpers import ParseError, Node, RuleMap, eat, parse, raise_null_error, skip_newlines
from dnjs.tokeniser_2 import (
    Token,
    TokenStream,
    eof,
    newline,
    unexpected,
    keyword,
    name,
    punctuation,
    literal,
    template,
)

rule_map = RuleMap()

# For overloading of , inside function calls
COMMA_PREC = 1


# -1 precedence -- never used
rule_map.register_null(-1, [")", "]", ":", "eof"])(raise_null_error)


# -1 precedence -- never used
@rule_map.register_null(-1, [name, literal])
def null_constant(token_stream: TokenStream, bp: int) -> Node:
    before = next(token_stream)
    skip_newlines(token_stream)
    return Node(before, [])


# 0 precedence -- doesn't bind until )
@rule_map.register_null(0, ["("])
def null_paren(token_stream: TokenStream, bp: int) -> Node:
    """ Arithmetic grouping """
    next(token_stream)
    r = parse(rule_map, token_stream, bp)
    eat(token_stream, ")")
    return r


@rule_map.register_null(27, ["+", "!", "~", "-"])
def null_prefix_op(token_stream: TokenStream, bp: int) -> Node:
    """Prefix operator.

    Low precedence:  return, raise, etc.
      return x+y is return (x+y), not (return x) + y

    High precedence: logical negation, bitwise complement, etc.
      !x && y is (!x) && y, not !(x && y)
    """
    before = next(token_stream)
    r = parse(rule_map, token_stream, bp)
    return Node(before, [r])


# 29 -- binds to everything except function call, indexing, postfix ops
@rule_map.register_null(29, ["++", "--"])
def null_inc_dec(token_stream: TokenStream, bp: int) -> Node:
    """ ++x or ++x[1] """
    before = next(token_stream)
    right = parse(rule_map, token_stream, bp)
    if right.token.type not in ("name", "get"):
        raise ParseError("Can't assign to %r (%s)" % (right, right.token))
    return Node(before, [right])


@rule_map.register_left(31, ["++", "--"])
def left_inc_dec(token_stream: TokenStream, rbp: int, left: Node) -> Node:
    """For i++ and i--"""
    before = next(token_stream)
    if left.token.type not in ("name", "get"):
        raise ParseError("Can't assign to %r (%s)" % (left, left.token))
    before.type = "post" + before.type
    return Node(before, [left])


@rule_map.register_left(31, ["["])
def left_index(token_stream: TokenStream, rbp: int, left: Node) -> Node:
    """ index f[x+1] """
    # f[x] or f[x][y]
    before = next(token_stream)
    if left.token.type not in ("name", "get"):
        raise ParseError("%s can't be indexed" % left)
    index = parse(rule_map, token_stream, 0)
    eat(token_stream, "]")

    before.type = "get"
    return Node(before, [left, index])


@rule_map.register_left(5, ["?"], is_left_right_assoc=True)
def left_ternary(token_stream: TokenStream, rbp: int, left: Node) -> Node:
    """ e.g. a > 1 ? x : y """
    # 0 binding power since any operators allowed until ':'.  See:
    #
    # http://en.cppreference.com/w/c/language/operator_precedence#cite_note-2
    #
    # "The expression in the middle of the conditional operator (between ? and
    # :) is parsed as if parenthesized: its precedence relative to ?: is
    # ignored."
    before = next(token_stream)
    true_expr = parse(rule_map, token_stream, 0)

    eat(token_stream, ":")
    false_expr = parse(rule_map, token_stream, rbp)
    children = [left, true_expr, false_expr]
    return Node(before, children)


@rule_map.register_left(25, ["*", "/", "%"])
@rule_map.register_left(23, ["+", "-"])
@rule_map.register_left(21, ["<<", ">>"])
@rule_map.register_left(19, ["<", ">", "<=", ">="])
@rule_map.register_left(17, ["!=", "=="])
@rule_map.register_left(15, ["&"])
@rule_map.register_left(13, ["^"])
@rule_map.register_left(11, ["|"])
@rule_map.register_left(9, ["&&"])
@rule_map.register_left(7, ["||"])
# Right associative: 2 ** 3 ** 2 == 2 ** (3 ** 2)
# Binds more strongly than negation.
@rule_map.register_left(29, ["**"], is_left_right_assoc=True)
def left_binary_op(token_stream: TokenStream, rbp: int, left: Node) -> Node:
    """ Normal binary operator like 1+2 or 2*3, etc. """
    before = next(token_stream)
    return Node(before, [left, parse(rule_map, token_stream, rbp)])


@rule_map.register_left(
    3,
    ["=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|="],
    is_left_right_assoc=True,
)
def left_assign(token_stream: TokenStream, rbp: int, left: Node) -> Node:
    """ Normal binary operator like 1+2 or 2*3, etc. """
    # x += 1, or a[i] += 1
    before = next(token_stream)
    if left.token.type not in ("name", "get"):
        raise ParseError("Can't assign to %r (%s)" % (left, left.token))
    return Node(before, [left, parse(rule_map, token_stream, rbp)])


@rule_map.register_left(COMMA_PREC, [","])
def left_comma(token_stream: TokenStream, rbp: int, left: Node) -> Node:
    """foo, bar, baz

    Could be sequencing operator, or tuple without parens
    """
    before = next(token_stream)
    r = parse(rule_map, token_stream, rbp)
    if left.token.type == ",":  # Keep adding more children
        left.children.append(r)
        return left
    children = [left, r]
    return Node(before, children)


@rule_map.register_left(31, ["("])
def left_func_call(token_stream: TokenStream, rbp: int, left: Node) -> Node:
    """ Function call f(a, b). """
    before = next(token_stream)
    children = [left]
    # f(x) or f[i](x)
    if left.token.type not in ("name", "get"):
        raise ParseError("%s can't be called" % left)
    while True:
        if token_stream.current.type == ")":
            break
        # We don't want to grab the comma, e.g. it is NOT a sequence operator.  So
        # set the precedence to 5.
        children.append(parse(rule_map, token_stream, COMMA_PREC))
        if token_stream.current.type == ",":
            eat(token_stream, ",")
    eat(token_stream, ")")
    before.type = "call"
    return Node(before, children)

