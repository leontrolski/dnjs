# Writing a JS interpreter in Python

Let's write a Pratt parser and an interpreter for a subset of JS with Python(/go)!

This type of parser has become fairly popular due to it's simplicity and how easily it handles, in fact I'm part of a [long lineage](https://www.oilshell.org/blog/2017/03/31.html) of bloggers - it's the "monad is a burrito" of parsing posts. I thought I'd bother writing up my attempt as I had a fun time writing it and was particularly happy with the brevity of the resulting code - I think this really exposes how lovely a parsing method it is. Thank you thank you [Andy C](https://andychu.net/) for bringing it into my life.

Also, I feel I gained some deeper understanding of JS in writing it, so hopefully you will gain some in reading.

## Some background on "why?"

<fold me>

[dnjs]() sits between JSON and Javascript, here's the features on top of JSON:

- functions
- templates
- rest vars
- ternary operator
- equality comparisons
- top-level assignments, imports, exports
- inbuilt functions: .map, .filter, .length, .reduce, .includes, Object.entries, Object.fromEntries, dedent, html generation

It turns out these features are just enough for a great config language/template language/jq replacement. They're also small enough to be able to implement in a reasonable time in a host language (the Python version is around 500 lines). I'm using it on personal projects

blahblah balh, just link instead?

## Tokenising

Our tokeniser takes some source code and splits it into tokens, it has one attribute and one method:

```
.current: Token
.advance() -> None
```

Let's see how they work:

```
>>> from dnjs import tokeniser

>>> source = '[1, "two", foo]'
>>> t = tokeniser.TokenStream.from_source(source)

>>> t.current
Token(type='[',      value='[',     pos=0,  lineno=1, linepos=0 )

>>> t.advance()
>>> t.current
Token(type='number', value='1',     pos=1,  lineno=1, linepos=1 )

# we keep repeating t.advance(), t.current

Token(type=',',      value=',',     pos=2,  lineno=1, linepos=2 )
Token(type='string', value='"two"', pos=4,  lineno=1, linepos=4 )
Token(type=',',      value=',',     pos=9,  lineno=1, linepos=9 )
Token(type='name',   value='foo',   pos=11, lineno=1, linepos=11)
Token(type=']',      value=']',     pos=14, lineno=1, linepos=14)
Token(type='eof',    value='eof',   pos=16, lineno=2, linepos=0 )
```

Makes sense? Great. I'll leave implementing the tokeniser to your imagination, here's [dnjs]()'s if you're interested.

The type of a token is one of the following:

```
name string number template literal
= => ( ) { } [ ] , : . ... ? === ` import from export default const
eof unexpected
```

## JS lisp

All [dnjs's parsing tests]() assert against [S-expression](https://en.wikipedia.org/wiki/S-expression) representations of the parsed code. Let's look at some examples - a line of JS followed by a line of equivalent S-expression - hopefully it'll be obvious what's going on.

```
[1, 2, null]
([ 1 2 null)

foo.bar === 4
(=== (. foo bar) 4)

{foo: 2, bar: 3, ...a}
({ (: foo 2) (: bar 3) (... a))

f(3, 4, 5)
($ f (* 3 4 5))

const bar = {}
(const (= bar ({)))

import m from "mithril"
(import (from m "mithril"))

(a) => [42]
(=> (d* a) '([ 42))

const f = (a, b, c) => ({"foo": [1]})
(const (= f (=> (d* a b c) '(( ({ (: "foo" ([ 1)))))))

(a === 3) ? "foo" : 2
(? (( (=== a 3)) '"foo" '2)

const a = `  hi ${first}${second}`
(const (= a (` `  hi ${ first }${ second }`)))
```

So, each S-expression is of the form:

```
(operator child child)
```

If we have no child, we have an "atom", one child, the operator is "unary", two children is "binary", three children is "ternary" and any number of children is "variadic".

Some of the S-expressions are quoted like this:

```
'(operator child child)
```

This is an instruction to the interpreter not to immediately evaluate the expression (used in the case of function return values and ternary operator return values).

In memory, we represent the S-expressions by the folowing type:

```@dataclass
class Node:
    token: t.Token
    is_quoted: bool
    children: List[Node]
```

If we do:

```
str(some_node)
```

We get the S-expression version.

Note we just use the token's type as the operator.

As you may have noticed, we've invented some artificial operators that weren't returned by the tokeniser, they are:

```
$               -  apply a function to some arguments
*               -  a group of arguments
dname d* d[ d{  -  dumb versions of name * [ {
```

Now go back to the examples and check they make sense.

## Parsing

We're now going to look at a reduced version of `dnjs`'s parser, our aim is going to be to parse a statement like this:

```token_stream = t.TokenStream.from_source("foo.bar === [1, 2, 3]")
assert str(parse(token_stream, 0)) == "(=== (. foo bar) ([ 1 2 3))"```

The Pratt parsing algorithm is in essence:

```
def parse(rbp) -> Node
    before = token_stream.current

    if before is an atom:
        node = Node(before)

    elif before is an array, object, etc:
        children = []
        while token_stream.current is not ] or }:
            children.append(parse(rbp))
        node = Node(before, children)

    return infix(rbp, node)

def infix(rbp, left) -> Node:
    before = token_stream.current

    if before is === :
        next_rbp = 2
        if rbp >= next_rbp:
            return left
        right = parse(next_rbp)
        return infix(rbp, Node(before, [left, right])

    elif before is . :
        next_rbp = 3
        ... for all infix operators

    else:
        return left
```

[Here]() is the demo parser, we're going to follow though step-by-step.

Our tokens are as follows:

```
Token(type='name',   value='foo')
Token(type='.',      value='.'  )
Token(type='name',   value='bar')
Token(type='===',    value='===')
Token(type='[',      value='['  )
Token(type='number', value='1'  )
Token(type=',',      value=','  )
Token(type='number', value='2'  )
Token(type=',',      value=','  )
Token(type='number', value='3'  )
Token(type=']',      value=']'  )
```

Let's follow this parsing process, I'm going to represent the nodes with the S-expression syntax.

├── parse(rbp=0) before is foo
├── hit number|name branch
│   ├── infix(rbp=0, left=foo) before is .
│   ├── hit . branch
│   │   ├── parse(rbp=3) before is bar
│   │   ├── hit number|name branch
│   │   │   ├── infix(rbp=3, left=bar) before is ===
│   │   │   ├── hit === branch
│   │   │   ├── hit high precedence branch
│   │   │   └── return bar
│   │   └── return bar
│   ├── right = bar
│   │   ┌── infix(rbp=0, left=(. foo bar)) before is ===
│   │   ├── hit === branch
│   │   │   ├── parse(rbp=2) before is [
│   │   │   ├── hit [ branch
│   │   │   │   ├── parse(rbp=0) before is 1
│   │   │   │   ├── hit number|name branch
│   │   │   │   │   ├── infix(rbp=0, left=1) before is ,
│   │   │   │   │   ├── didn't hit any branch
│   │   │   │   │   └── return 1
│   │   │   │   └── return 1
│   │   │   │   ┌── parse(rbp=0) before is 2
│   │   │   │   ├── hit number|name branch
│   │   │   │   │   ├── infix(rbp=0, left=2) before is ,
│   │   │   │   │   ├── didn't hit any branch
│   │   │   │   │   └── return 2
│   │   │   │   └── return 2
│   │   │   │   ┌── parse(rbp=0) before is 3
│   │   │   │   ├── hit number|name branch
│   │   │   │   │   ├── infix(rbp=0, left=3) before is ]
│   │   │   │   │   ├── didn't hit any branch
│   │   │   │   │   └── return 3
│   │   │   │   └── return 3
│   │   │   │   ┌── infix(rbp=2, left=([ 1 2 3)) before is eof
│   │   │   │   ├── didn't hit any branch
│   │   │   │   └── return ([ 1 2 3)
│   │   │   └── return ([ 1 2 3)
│   │   ├── right = ([ 1 2 3)
│   │   │   ┌── infix(rbp=0, left=(=== (. foo bar) ([ 1 2 3))) before is eof
│   │   │   ├── didn't hit any branch
│   │   │   └── return (=== (. foo bar) ([ 1 2 3))
│   │   └── return (=== (. foo bar) ([ 1 2 3))
│   └── return (=== (. foo bar) ([ 1 2 3))
└── return (=== (. foo bar) ([ 1 2 3))


# Interpreting

Coming soon...
