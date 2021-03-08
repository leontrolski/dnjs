package main

import (
	"encoding/json"
	"fmt"
	"github.com/stretchr/testify/assert"
	"testing"
)

func i(t *testing.T, s string) string {
	tokenStream := TokenStreamFromSource(s)
	module, err := interpret(&tokenStream)
	if err != nil {
		fmt.Println(err)
	}
	assert.Nil(t, err)
	jsonString, err := json.Marshal(module.Value)
	assert.Nil(t, err)
	return string(jsonString[:])
}

func fileDefault(t *testing.T, filepath string) string {
	tokenStream, _ := TokenStreamFromFilepath(filepath)
	module, err := interpret(&tokenStream)
	if err != nil {
		fmt.Println(err)
	}
	assert.Nil(t, err)
	jsonString, err := json.Marshal(module.DefaultExport)
	assert.Nil(t, err)
	return string(jsonString[:])
}

func fileNamed(t *testing.T, filepath string, name string) string {
	tokenStream, _ := TokenStreamFromFilepath(filepath)
	module, err := interpret(&tokenStream)
	if err != nil {
		fmt.Println(err)
	}
	assert.Nil(t, err)
	jsonString, err := json.Marshal(module.Exports[name])
	assert.Nil(t, err)
	return string(jsonString[:])
}

func getErr(t *testing.T, s string) string {
	tokenStream := TokenStreamFromSource(s)
	_, err := interpret(&tokenStream)
	return err.Error()
}

func TestLiteralValue(t *testing.T) {
	assert.Equal(t, i(t, "null"), `null`)
}

func TestEq(t *testing.T) {
	assert.Equal(t, i(t, "(1)"), `1`)
	assert.Equal(t, i(t, "1 === 1"), `true`)
	assert.Equal(t, i(t, "2 === 2"), `true`)
	assert.Equal(t, i(t, "1.0 === 1.0"), `true`)
	assert.Equal(t, i(t, "1.0 === 2.0"), `false`)
	assert.Equal(t, i(t, "\"foo\" === (\"foo\")"), `true`)
	assert.Equal(t, i(t, "\"foo\" === \"bar\""), `false`)
}

func TestObjectAndDot(t *testing.T) {
	assert.Equal(t, i(t, "{foo: 42}"), `{"foo":42}`)
	assert.Equal(t, i(t, "({foo: 42}).foo"), `42`)
	assert.Equal(t, i(t, "({foo: 42}).bar"), "\"\\u003cundefined\\u003e\"")
	assert.Equal(t, getErr(t, "({foo: 42}).bar.rar"), `<ParserError line:1>
cannot get .rar, value is undefined
({foo: 42}).bar.rar
_______________^`)
}

func TestAssignment(t *testing.T) {
	assert.Equal(t, i(t, "const foo = 5\nfoo"), `5`)
	assert.Equal(t, getErr(t, "const foo = 5\nbar"), `<ParserError line:2>
variable bar is not in scope
bar
^`)
}

func TestEllipsis(t *testing.T) {
	assert.Equal(t, i(t, "const a = {foo: 1}\n{bar: 2, ...a}"), `{"bar":2,"foo":1}`)
	assert.Equal(t, getErr(t, "const a = 42\n{bar: 2, ...a}"), `<ParserError line:2>
must be of type: {
{bar: 2, ...a}
____________^`)
	assert.Equal(t, i(t, "const a = [1]\n[...a, 2]"), `[1,2]`)
	assert.Equal(t, getErr(t, "const a = 1\n[...a, 2]"), `<ParserError line:2>
must be of type: [
[...a, 2]
____^`)
}

func TestTernaryOperator(t *testing.T) {
	assert.Equal(t, i(t, "true ? 1 : 2"), `1`)
	assert.Equal(t, i(t, "false ? 1 : 2"), `2`)
}

func TestBacktick(t *testing.T) {
	assert.Equal(t, i(t, "`foo${1}bar`"), `"foo1bar"`)
	assert.Equal(t, i(t, "`foo${4.2}bar`"), `"foo4.2bar"`)
	assert.Equal(t, i(t, "`foo${\"baz\"}bar`"), `"foobazbar"`)
	assert.Equal(t, i(t, "`foo${\"baz\"}bar`"), `"foobazbar"`)
}

func TestFuncApply(t *testing.T) {
	assert.Equal(t, i(t, "(a => [a, 2])(1)"), `[1,2]`)
	assert.Equal(t, getErr(t, "[](1)"), `<ParserError line:1>
attempting to call non-function
[](1)
__^`)
	assert.Equal(t, i(t, "(([a, b]) => [b, a])([2, 1])"), `[1,2]`)
	assert.Equal(t, i(t, "(([a, b], c) => [b, a, c])([2, 1], 3)"), `[1,2,3]`)
	assert.Equal(t, getErr(t, "(([a, b]) => [b, a])({})"), `<ParserError line:1>
cannot unpack argument
(([a, b]) => [b, a])({})
_____________________^`)

	assert.Equal(t, i(t, "[1, 2, 3].length"), `3`)

	assert.Equal(t, getErr(t, "[1, 2, 3].map()"), `<ParserError line:1>
expected 1 argument
[1, 2, 3].map()
_____________^`)
	assert.Equal(t, getErr(t, "[1, 2, 3].map(4)"), `<ParserError line:1>
attempting to call non-function
[1, 2, 3].map(4)
_____________^`)
	assert.Equal(t, i(t, "[1, 2].map(n => ({foo: n}))"), `[{"foo":1},{"foo":2}]`)

	assert.Equal(t, i(t, "[[1, 2], [3], [4, 5]].reduce((a, b)=>[...a, ...b], [])"), `[1,2,3,4,5]`)

	assert.Equal(t, i(t, "[1, 2].includes(1)"), `true`)
	assert.Equal(t, i(t, "[1, 2].includes(9)"), `false`)

	assert.Equal(t, i(t, "Object.entries({foo: 1})"), `[["foo",1]]`)
	assert.Equal(t, getErr(t, "Object.entries()"), `<ParserError line:1>
expected 1 argument
Object.entries()
______________^`)
	assert.Equal(t, getErr(t, "Object.entries([])"), `<ParserError line:1>
can only get entries of {
Object.entries([])
______________^`)

	assert.Equal(t, i(t, "Object.fromEntries([[\"foo\", 1]])"), `{"foo":1}`)
	assert.Equal(t, getErr(t, "Object.fromEntries(2)"), `<ParserError line:1>
can only get entries of [
Object.fromEntries(2)
__________________^`)
	assert.Equal(t, getErr(t, "Object.fromEntries([2])"), `<ParserError line:1>
must be all (string, Value) pairs
Object.fromEntries([2])
__________________^`)
}

func TestFileRest(t *testing.T) {
	assert.Equal(t,
		fileDefault(t, "../test/data/rest.dn.js"),
		`{"bar":[42,43],"key":["item0","item1",3.14,42,43,true,{"bar":[42,43]}]}`,
	)
}

func TestFileThisImports(t *testing.T) {
	assert.Equal(t,
		fileDefault(t, "../test/data/thisImports.dn.js"),
		`{"foo":["DEFAULT",[{"A":1}],"B"]}`,
	)
}

func TestFileFunctions(t *testing.T) {
	// assert.Equal(t,
	// 	fileNamed(t, "../test/data/function.dn.js", "f"),
	// 	`[1,2,42]`,
	// )
	// actual = get_named_export(data_dir / "function.dn.js", "g")
	// assert actual() == 42.0
}

func TestFileFunctionCall(t *testing.T) {
	assert.Equal(t,
		fileDefault(t, "../test/data/functionCall.dn.js"),
		`{"hello":42}`,
	)
}

func TestFileTernary(t *testing.T) {
	assert.Equal(t,
		fileNamed(t, "../test/data/ternary.dn.js", "f"),
		`"f"`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/ternary.dn.js", "t"),
		`"t"`,
	)
}

func TestFileMap(t *testing.T) {
	assert.Equal(t,
		fileNamed(t, "../test/data/map.dn.js", "a"),
		`[{"myI":0,"myV":1},{"myI":1,"myV":2},{"myI":3,"myV":200}]`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/map.dn.js", "b"),
		`[{"i":0,"k":"3","v":4}]`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/map.dn.js", "c"),
		`{"5":6,"7":8}`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/map.dn.js", "d"),
		`true`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/map.dn.js", "e"),
		`false`,
	)
}

func TestMNodes(t *testing.T) {
	assert.Equal(t,
		fileNamed(t, "../test/data/node.dn.js", "a"),
		`{"attrs":{"className":""},"children":[],"tag":"br"}`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/node.dn.js", "b"),
		`{"attrs":{"className":"foo bar baz","id":"rarr"},"children":[{"attrs":{"className":"","id":"qux"},"children":[{"attrs":{"className":""},"children":["0"],"tag":"li"},{"attrs":{"className":""},"children":["1"],"tag":"li"},{"attrs":{"className":""},"children":["2"],"tag":"li"}],"tag":"ul"},"apple",{"attrs":{"className":""},"children":[],"tag":"br"}],"tag":"div"}`,
	)
	assert.Equal(t, getErr(t, "m()"), `<ParserError line:1>
m(...) must be called with more than one argument
m()
_^`)
	assert.Equal(t, getErr(t, "m(1)"), `<ParserError line:1>
first argument to m(...) must be a string
m(1)
__^`)
	assert.Equal(t, getErr(t, `m("div", ()=>null)`), `<ParserError line:1>
attributes must be a map of string to value
m("div", ()=>null)
___________^`)
	assert.Equal(t, getErr(t, `m("div", {class: 1})`), `<ParserError line:1>
class attribute must be an array of strings
m("div", {class: 1})
_________^`)
	assert.Equal(t, getErr(t, `m("div", {class: [1]})`), `<ParserError line:1>
class attribute must be an array of strings
m("div", {class: [1]})
_________^`)
	assert.Equal(t, getErr(t, `m("div", {}, ()=>null)`), `<ParserError line:1>
one f the arguments to m(...) is not renderable
m("div", {}, ()=>null)
_^`)
}

func TestFileTemplate(t *testing.T) {
	assert.Equal(t,
		fileNamed(t, "../test/data/template.dn.js", "a"),
		`"foo"`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/template.dn.js", "b"),
		`"hello oli,\nyou are 29"`,
	)
	assert.Equal(t,
		fileNamed(t, "../test/data/template.dn.js", "c"),
		`{"bar":"\"baz\"","foo":"\"hullo\"\ncat foo.txt \u003e bar\ntail /dev/null"}`,
	)
}
