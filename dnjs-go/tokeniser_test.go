package main

import (
	"fmt"
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestToken(t *testing.T) {
	myPath := "baz"
	got := Token{
		Type:     "foo",
		Value:    "bar",
		Filepath: &myPath,
		Pos:      0,
		Lineno:   0,
		Linepos:  0,
	}
	actual := got.String()
	expected := "<foo bar>"
	assert.Equal(t, actual, expected)
}

func TestTokeniserBasic(t *testing.T) {
	tokenStream, _ := TokenStreamFromFilepath("../test/data/simple.dn.js")
	actual := tokenStream.Current.String()
	expected := "<str \"12世界5\">"
	assert.Equal(t, actual, expected)

	tokenStream.Advance()
	actual = tokenStream.Current.String()
	expected = "<str \"90世界\">"
	assert.Equal(t, actual, expected)

	tokenStream.Advance()
	actual = tokenStream.Current.String()
	expected = "<str \"bar\">"
	assert.Equal(t, actual, expected)

	tokenStream.Advance()
	actual = tokenStream.Current.String()
	expected = "<\x03 \x03>"
	assert.Equal(t, actual, expected)
}

func l(s string) []string {
	vs := []string{}
	tokenStream := TokenStreamFromSource(s)
	for {
		token := tokenStream.Current
		tokenStream.Advance()
		if token.Type == eof {
			break
		}
		vs = append(vs, fmt.Sprintf("%s %s", token.Type, token.Value))
	}
	return vs
}

func TestEmpty(t *testing.T) {
	assert.Equal(t, l(" "), []string{})
	assert.Equal(t, l(""), []string{})
}

func TestUnexpected(t *testing.T) {
	assert.Equal(t, l("±"), []string{"unexpected ±"})
}

func TestNumber(t *testing.T) {
	assert.Equal(t, l("1"), []string{"number 1"})
	assert.Equal(t, l("-1.5"), []string{"number -1.5"})
	assert.Equal(t, l("-1..5"), []string{"unexpected -1..", "number 5"})
}

func TestPunctuation(t *testing.T) {
	assert.Equal(t, l(". "), []string{". ."})
	assert.Equal(t, l("."), []string{". ."})
	assert.Equal(t, l("..."), []string{"... ..."})
	assert.Equal(t, l("==="), []string{"=== ==="})
	assert.Equal(t, l("=>."), []string{"=> =>", ". ."})
	assert.Equal(t, l("=>."), []string{"=> =>", ". ."})
	assert.Equal(t, l(".."), []string{"unexpected .."})
	assert.Equal(t, l("...."), []string{"... ...", ". ."})
	assert.Equal(t, l("..=>"), []string{"unexpected ..", "=> =>"})
}

func TestVarAndKeyword(t *testing.T) {
	assert.Equal(t, l("import"), []string{"import import"})
	assert.Equal(t, l("importfoo"), []string{"name importfoo"})
	assert.Equal(t, l("from _bar const"), []string{"from from", "name _bar", "const const"})
}

func TestString(t *testing.T) {
	assert.Equal(t, l("\"foo\""), []string{"str \"foo\""})
	assert.Equal(t, l("\"foo\\\"bar\""), []string{"str \"foo\"bar\""})
	assert.Equal(t, l("\"foo\\\\\" 42"), []string{"str \"foo\\\"", "number 42"})
	assert.Equal(t, l("42\"foo"), []string{"number 42", "unexpected \"foo"})
	assert.Equal(t, l("\"foo\nbar\""), []string{"unexpected \"foo\n", "name bar", "unexpected \""})
}

func TestTemplate(t *testing.T) {
	assert.Equal(t, l("``"), []string{"` ``"})
	assert.Equal(t, l("`foo`"), []string{"` `foo`"})
	assert.Equal(t, l("`foo\\`bar`"), []string{"` `foo`bar`"})
	assert.Equal(t, l("`foo\\\\` 42"), []string{"` `foo\\`", "number 42"})
	assert.Equal(t, l("`foo${42}bar`"), []string{"` `foo${", "number 42", "template }bar`"})
	assert.Equal(t, l("`foo${a[`inner${1}2${3}`]}bar`"), []string{"` `foo${", "name a", "[ [", "` `inner${", "number 1", "template }2${", "number 3", "template }`", "] ]", "template }bar`"})
	assert.Equal(t, l("`foo\nbar`"), []string{"` `foo\nbar`"})
	assert.Equal(t, l("`${`${a}--${b}`}`"), []string{"` `${", "` `${", "name a", "template }--${", "name b", "template }`", "template }`"})
	assert.Equal(t, l("{`foo`}"), []string{"{ {", "` `foo`", "} }"})
}

func TestLineNumbers(t *testing.T) {
	resetGlobalCounter()

	var eat = func(reader *TokenStream) Token {
		before := reader.Current
		reader.Advance()
		return before
	}
	memory1 := "memory://1"
	memory2 := "memory://2"
	memory3 := "memory://3"
	memory4 := "memory://4"
	reader := TokenStreamFromSource("012  56")
	assert.Equal(t, eat(&reader), Token{"number", "012", &memory1, 0, 1, 0})
	assert.Equal(t, eat(&reader), Token{"number", "56", &memory1, 5, 1, 5})
	assert.Equal(t, eat(&reader).Type, eof)

	reader = TokenStreamFromSource("0\n23\n567\n")
	assert.Equal(t, eat(&reader), Token{"number", "0", &memory2, 0, 1, 0})
	assert.Equal(t, eat(&reader), Token{"number", "23", &memory2, 2, 2, 0})
	assert.Equal(t, eat(&reader), Token{"number", "567", &memory2, 5, 3, 0})
	assert.Equal(t, eat(&reader).Type, eof)

	reader = TokenStreamFromSource("012//56\n8\n")
	assert.Equal(t, eat(&reader), Token{"number", "012", &memory3, 0, 1, 0})
	assert.Equal(t, eat(&reader), Token{"number", "8", &memory3, 8, 2, 0})
	assert.Equal(t, eat(&reader).Type, eof)

	reader = TokenStreamFromSource("0\n`3\n5`\n8")
	assert.Equal(t, eat(&reader), Token{"number", "0", &memory4, 0, 1, 0})
	assert.Equal(t, eat(&reader), Token{"`", "`3\n5`", &memory4, 2, 2, 0})
	assert.Equal(t, eat(&reader), Token{"number", "8", &memory4, 8, 4, 0})
	assert.Equal(t, eat(&reader).Type, eof)
}

func TestCombined(t *testing.T) {
	assert.Equal(t, l(".12.6"), []string{". .", "number 12.6"})
}

func TestComments(t *testing.T) {
	text := `{
        "key": ["item0", "not//a//comment", 3.14, true]  // another {} comment
        // a comment
        //
    }`
	expected := []string{
		"{ {",
		"str \"key\"",
		": :",
		"[ [",
		"str \"item0\"",
		", ,",
		"str \"not//a//comment\"",
		", ,",
		"number 3.14",
		", ,",
		"literal true",
		"] ]",
		"} }",
	}
	assert.Equal(t, l(text), expected)
}
