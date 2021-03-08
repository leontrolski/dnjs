package main

import (
	"github.com/stretchr/testify/assert"
	"strings"
	"testing"
)

func p(t *testing.T, s string) string {
	tokenStream := TokenStreamFromSource(s)
	statements, err := ParseStatements(&tokenStream)
	if err != nil {
		t.Errorf(err.Error())
	}
	statementStrings := []string{}
	for _, statement := range statements {
		statementStrings = append(statementStrings, statement.String())
	}
	return strings.Join(statementStrings, "\n")
}

func TestNode(t *testing.T) {
	myPath := "baz"
	token := Token{
		Type:     "foo",
		Value:    "bar",
		Filepath: &myPath,
		Pos:      0,
		Lineno:   0,
		Linepos:  0,
	}
	node := Node{token, []Node{}, false}
	assert.Equal(t, node.String(), "(foo)")
}

func TestParseEmpty(t *testing.T) {
	assert.Equal(t, p(t, ""), "")
}

func TestParseLiteralAndNames(t *testing.T) {
	assert.Equal(t, p(t, "1"), "1")
	assert.Equal(t, p(t, "1.4"), "1.4")
	assert.Equal(t, p(t, "\"foo\""), "\"foo\"")
	assert.Equal(t, p(t, "bar"), "bar")
	assert.Equal(t, p(t, "true"), "true")
}

func TestParseInfixes(t *testing.T) {
	assert.Equal(t, p(t, "1 === 2"), "(=== 1 2)")
	assert.Equal(t, p(t, "foo.bar"), "(. foo bar)")
	assert.Equal(t, p(t, "foo.bar === 4"), "(=== (. foo bar) 4)")
	assert.Equal(t, p(t, "foo.bar.baz"), "(. (. foo bar) baz)")
	assert.Equal(t, p(t, "(foo.bar === baz).qux"), "(. (( (=== (. foo bar) baz)) qux)")
	assert.Equal(t, p(t, "[foo.bar === baz.qux]"), "([ (=== (. foo bar) (. baz qux)))")
}

func TestFunctionCall(t *testing.T) {
	assert.Equal(t, p(t, "f(3, 4, 5)"), "($ f (* 3 4 5))")
	assert.Equal(t, p(t, "f(3, 4, g(5, 6 === 7))"), "($ f (* 3 4 ($ g (* 5 (=== 6 7)))))")
	assert.Equal(t, p(t, "f(3\n, 4, g(5, \n6 === 7),)"), "($ f (* 3 4 ($ g (* 5 (=== 6 7)))))")
}

func TestArray(t *testing.T) {
	assert.Equal(t, p(t, "[]"), "([)")
	assert.Equal(t, p(t, "[1, 2, null]"), "([ 1 2 null)")
	assert.Equal(t, p(t, "[1, [2], null]"), "([ 1 ([ 2) null)")
	assert.Equal(t, p(t, "[1, 2, [3, [4, 5]], null]"), "([ 1 2 ([ 3 ([ 4 5)) null)")
}

func TestObject(t *testing.T) {
	assert.Equal(t, p(t, "{}"), "({)")
	assert.Equal(t, p(t, "{\"foo\": 2}"), "({ (: \"foo\" 2))")
	assert.Equal(t, p(t, "{foo: 2, bar: 3, ...a}"), "({ (: foo 2) (: bar 3) (... a))")
	assert.Equal(t, p(t, "{foo: [1, {\"bar\": 3}],}"), "({ (: foo ([ 1 ({ (: \"bar\" 3)))))")
}

func TestComment(t *testing.T) {
	text := `
        {
            "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
            // a comment
            //
        }
    `
	actual := p(t, text)
	expected := `({ (: "key" ([ "item0" "not//a//comment" 3.14 true)))`
	assert.Equal(t, actual, expected)
}

func TestImport(t *testing.T) {
	text := `
        import m from "mithril"

        import { base, form } from "./base.dn.js"

        {
            key: ["item0", "item1", 3.14, true],
        }
	`
	actual := p(t, text)
	expected := "(import (from m \"mithril\"))\n" +
		"(import (from (d{ base form) \"./base.dn.js\"))\n" +
		"({ (: key ([ \"item0\" \"item1\" 3.14 true)))"
	assert.Equal(t, actual, expected)
}

func TestAssignmentsRest(t *testing.T) {
	text := `
        const foo = 45
        const bar = {}
        {"key": ["item0", "item1", 3.14, ...foo, true, bar], ...foo.bar, baz: 12}
	`
	actual := p(t, text)
	expected := "(const (= foo 45))\n" +
		"(const (= bar ({)))\n" +
		"({ (: \"key\" ([ \"item0\" \"item1\" 3.14 (... foo) true bar)) (... (. foo bar)) (: baz 12))"
	assert.Equal(t, actual, expected)
}

func TestExport(t *testing.T) {
	text := `
        export default [6]
        export const base = 42

        {"key": ["item0", "item1", 3.14, true]}
	`
	actual := p(t, text)
	expected := "(export (default ([ 6)))\n" +
		"(export (const (= base 42)))\n" +
		"({ (: \"key\" ([ \"item0\" \"item1\" 3.14 true)))"
	assert.Equal(t, actual, expected)
}

func TestFunctions(t *testing.T) {
	text := `
        const a = (1)
        const f = () => 42
        export default (a) => a
        export const otherF = (a, b, c) => ({"foo": [1]})
        const foo = [f(), otherF(a, b, c)]
        foo(1)(2, 3)(4)
    `
	actual := p(t, text)
	expected := `(const (= a (( 1)))
(const (= f (=> (d*) '42)))
(export (default (=> (d* a) 'a)))
(export (const (= otherF (=> (d* a b c) '(( ({ (: "foo" ([ 1))))))))
(const (= foo ([ ($ f (*)) ($ otherF (* a b c)))))
($ ($ ($ foo (* 1)) (* 2 3)) (* 4))`
	assert.Equal(t, actual, expected)

	assert.Equal(t, p(t, "const foo = (a, b) => m(c)"), "(const (= foo (=> (d* a b) '($ m (* c)))))")
}

func TestTernary(t *testing.T) {
	assert.Equal(t, p(t, `(a === 3) ? "foo" : "bar"`), `(? (( (=== a 3)) '"foo" '"bar")`)
	assert.Equal(t, p(t, `a === (3 ? "foo" : "bar")`), `(=== a (( (? 3 '"foo" '"bar")))`)
	assert.Equal(t, p(t, `a === 3 ? "foo" : "bar"`), `(? (=== a 3) '"foo" '"bar")`)

	actual := p(t, `
        a
            ? b
        : c
            ? d
            : e
	`)
	assert.Equal(t, actual, "(? a 'b '(? c 'd 'e))")
}

func TestMapAndFilter(t *testing.T) {
	actual := p(t, "const a = [4, 5, 6].map((v, i) => 42).filter((v, i) => (i === 0 ? v : null) )")
	assert.Equal(t, actual, "(const (= a ($ (. ($ (. ([ 4 5 6) map) (* (=> (d* v i) '42))) filter) (* (=> (d* v i) '(( (? (=== i 0) 'v 'null)))))))")

	actual = p(t, "const a = Object.entries(foo.bar).map(([k, v], i) => v)")
	assert.Equal(t, actual, "(const (= a ($ (. ($ (. Object entries) (* (. foo bar))) map) (* (=> (d* (d[ k v) i) 'v)))))")

	actual = p(t, "Object.fromEntries(a.b.map((v, i) => 42))")
	assert.Equal(t, actual, "($ (. Object fromEntries) (* ($ (. (. a b) map) (* (=> (d* v i) '42)))))")
}

func TestM(t *testing.T) {
	text := `
		const a = m("li", "hello")
		const a = m("li#my-li.foo.bar", "hello", [1, 2])
		m(".foo#my-li.bar")
    `
	actual := p(t, text)
	expected := "(const (= a ($ m (* \"li\" \"hello\"))))\n" +
		"(const (= a ($ m (* \"li#my-li.foo.bar\" \"hello\" ([ 1 2)))))\n" +
		"($ m (* \".foo#my-li.bar\"))"
	assert.Equal(t, actual, expected)
}

func TestTemplates(t *testing.T) {
	text := "const a = `hi`\n" +
		"const a = ``\n" +
		"const a = `hi ${first} and ${second} ${third} `\n" +
		"const a = `  hi ${first}${second}`\n" +
		"const a = `$${money.amount}.00`\n" +
		"const a = `many\n" +
		"${foo}\n" +
		"lin//es`\n" +
		"[`foo $${money.amount}.00`]\n" +
		"const b = `${`${a}--${b}`}`\n"

	actual := p(t, text)
	expected := "(const (= a (` `hi`)))\n" +
		"(const (= a (` ``)))\n" +
		"(const (= a (` `hi ${ first } and ${ second } ${ third } `)))\n" +
		"(const (= a (` `  hi ${ first }${ second }`)))\n" +
		"(const (= a (` `$${ (. money amount) }.00`)))\n" +
		"(const (= a (` `many\n" +
		"${ foo }\n" +
		"lin//es`)))\n" +
		"([ (` `foo $${ (. money amount) }.00`))\n" +
		"(const (= b (` `${ (` `${ a }--${ b }`) }`)))"
	assert.Equal(t, actual, expected)
}

func TestAssignTernary(t *testing.T) {
	assert.Equal(t, p(t, "const f = a === 2 ? foo : bar"), "(const (= f (? (=== a 2) 'foo 'bar)))")
	assert.Equal(t, p(t, "const f = () => a === 2 ? foo : bar"), "(const (= f (=> (d*) '(? (=== a 2) 'foo 'bar))))")
	assert.Equal(t, p(t, "() => g(a, [f(b => a === 1)])"), "(=> (d*) '($ g (* a ([ ($ f (* (=> (d* b) '(=== a 1))))))))")
}

func TestErrors(t *testing.T) {
	tokenStream := TokenStreamFromSource("{a: b, c d}")
	_, err := ParseStatements(&tokenStream)
	assert.Equal(t, err.Error(), `<ParserError line:1>
expected ',' got 'd'
{a: b, c d}
_________^`)

	tokenStream = TokenStreamFromSource("[a, b c]")
	_, err = ParseStatements(&tokenStream)
	assert.Equal(t, err.Error(), `<ParserError line:1>
expected ',' got 'c'
[a, b c]
______^`)

	tokenStream = TokenStreamFromSource("import a from \"b\" import c from \"d\"")
	_, err = ParseStatements(&tokenStream)
	assert.Equal(t, err.Error(), `<ParserError line:1>
expected statements to be on separate lines
import a from "b" import c from "d"
__________________^`)

	tokenStream = TokenStreamFromSource("[] []")
	_, err = ParseStatements(&tokenStream)
	assert.Equal(t, err.Error(), `<ParserError line:1>
expected statements to be on separate lines
[] []
___^`)

	tokenStream = TokenStreamFromSource("42\"foo")
	_, err = ParseStatements(&tokenStream)
	assert.Equal(t, err.Error(), `<ParserError line:1>
unexpected token
42"foo
__^`)

	tokenStream = TokenStreamFromSource("`foo${1}bar${")
	_, err = ParseStatements(&tokenStream)
	assert.Equal(t, err.Error(), "<ParserError line:1>\n"+
		"unexpected end of input\n"+
		"`foo${1}bar${\n"+
		"_____________^")

	tokenStream = TokenStreamFromSource("[===3]")
	_, err = ParseStatements(&tokenStream)
	assert.Equal(t, err.Error(), `<ParserError line:1>
can't be used in prefix position
[===3]
_^`)

	tokenStream = TokenStreamFromSource("foo = 5")
	_, err = ParseStatements(&tokenStream)
	assert.Contains(t, err.Error(), "token is not of type")

	tokenStream = TokenStreamFromSource("{a: b: c, d}")
	_, err = ParseStatements(&tokenStream)
	assert.Contains(t, err.Error(), "token is not of type")

	tokenStream = TokenStreamFromSource("() => {}")
	_, err = ParseStatements(&tokenStream)
	assert.Contains(t, err.Error(), "token is not of type")

	tokenStream = TokenStreamFromSource("{}.foo")
	_, err = ParseStatements(&tokenStream)
	assert.Contains(t, err.Error(), "token is not of type")

}
