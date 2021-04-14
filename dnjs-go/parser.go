package main

import (
	"fmt"
	"io/ioutil"
	"strings"
)

var lowPrec = 1
var colonPrec = 2
var highPrec = 999

type Node struct {
	Token    Token
	Children []Node
	IsQuoted bool
}

func (n Node) String() string {
	sExpression := n.Token.Value
	if !containsString(atoms, n.Token.Type) {
		childrenStrings := []string{}
		for _, c := range n.Children {
			childrenStrings = append(childrenStrings, c.String())
		}
		args := strings.Join(childrenStrings, " ")
		gap := ""
		if len(args) > 0 {
			gap = " "
		}
		sExpression = fmt.Sprintf("(%s%s%s)", n.Token.Type, gap, args)
	}
	if n.IsQuoted {
		sExpression = "'" + sExpression
	}
	return sExpression
}

type rulePrefix struct {
	F          func(*TokenStream, int) (Node, error)
	Precedence int
}
type ruleInfix struct {
	F          func(*TokenStream, int, Node) (Node, error)
	Precedence int
}

var prefix = map[string]rulePrefix{}
var infix = map[string]ruleInfix{}
var infixRightAssoc = map[string]bool{}

func ParseStatements(tokenStream *TokenStream) ([]Node, error) {
	statements := []Node{}
	if tokenStream.Current.Type == eof {
		return statements, nil
	}
	for {
		node, err := Parse(tokenStream, 0)
		if err != nil {
			return []Node{}, err
		}
		// wrap in statement
		statementToken := node.Token
		statementToken.Type = "statement"
		node = Node{statementToken, []Node{node}, false}
		node, err = convertChildren(node)
		if err != nil {
			return []Node{}, err
		}
		// convert back from statement
		node = node.Children[0]
		statements = append(statements, node)
		if tokenStream.Current.Type == eof {
			break
		}
		prevLineno := maxLineno(node, 0)
		if tokenStream.Current.Lineno <= prevLineno {
			return []Node{}, ParseError{"expected statements to be on separate lines", tokenStream.Current}
		}
	}
	return statements, nil
}

func Parse(tokenStream *TokenStream, rbp int) (Node, error) {
	rule, ok := prefix[tokenStream.Current.Type]
	if !ok {
		rule = rulePrefix{raiseUnexpectedError, highPrec}
	}
	node, err := rule.F(tokenStream, rule.Precedence)
	if err != nil {
		return Node{}, err
	}
	return parseInfix(tokenStream, rbp, node)
}

func parseInfix(tokenStream *TokenStream, rbp int, node Node) (Node, error) {
	rule, ok := infix[tokenStream.Current.Type]
	if !ok {
		rule = ruleInfix{raiseUnexpectedErrorInfix, highPrec}
	}
	ruleRbp := rule.Precedence
	_, isInfix := infixRightAssoc[tokenStream.Current.Type]
	if isInfix {
		ruleRbp = ruleRbp - 1
	}
	if rbp >= rule.Precedence {
		return node, nil
	}
	node, err := rule.F(tokenStream, ruleRbp, node)
	if err != nil {
		return Node{}, err
	}
	return parseInfix(tokenStream, rbp, node)
}

// Assert the value of the current token, then move to the next token.
func eat(tokenStream *TokenStream, tokenType string) error {
	if tokenStream.Current.Type != tokenType {
		return ParseError{
			fmt.Sprintf("expected '%s' got '%s'", tokenType, tokenStream.Current.Value),
			tokenStream.Current,
		}
	}
	tokenStream.Advance()
	return nil
}

func prefixAtom(tokenStream *TokenStream, bp int) (Node, error) {
	before := tokenStream.Current
	tokenStream.Advance()
	return Node{before, []Node{}, false}, nil
}

func prefixUnary(tokenStream *TokenStream, bp int) (Node, error) {
	before := tokenStream.Current
	tokenStream.Advance()
	child, err := Parse(tokenStream, bp)
	if err != nil {
		return Node{}, err
	}
	return Node{before, []Node{child}, false}, nil
}

// a === b becomes (=== a b)
func infixBinary(tokenStream *TokenStream, rbp int, left Node) (Node, error) {
	before := tokenStream.Current

	if before.Type == "=>" {
		// (a, b) => [1, 2] becomes (=> (* a b) '([ 1 2))
		// a => [1, 2] becomes (=> (* a) '([ 1 2))
		if left.Token.Type == name {
			left = Node{left.Token, []Node{left}, false}
		}
		left.Token.Type = many
	}

	var right Node
	var err error
	if before.Type == "(" {
		// in the case of ( as a infix binary operator, eg:
		// f(1, 2, 3) becomes ($ f (* 1 2 3))
		before.Type = apply
		right, err = Parse(tokenStream, rbp)
		right.Token.Type = many
	} else {
		tokenStream.Advance()
		right, err = Parse(tokenStream, rbp)
	}
	if err != nil {
		return Node{}, err
	}

	if before.Type == "=>" {
		right.IsQuoted = true
	}

	return Node{before, []Node{left, right}, false}, nil
}

// a > 1 ? x : y becomes (? (> a 1) x y)
func infixTernary(tokenStream *TokenStream, rbp int, left Node) (Node, error) {
	before := tokenStream.Current
	tokenStream.Advance()

	trueExpr, err := Parse(tokenStream, colonPrec)
	if err != nil {
		return Node{}, err
	}
	err = eat(tokenStream, ":")
	if err != nil {
		return Node{}, err
	}
	falseExpr, err := Parse(tokenStream, rbp)
	if err != nil {
		return Node{}, err
	}
	trueExpr.IsQuoted = true
	falseExpr.IsQuoted = true
	return Node{before, []Node{left, trueExpr, falseExpr}, false}, nil
}

// {a: 1, ...x} becomes ({ (: a 1) (... x))"""
func prefixVariadic(tokenStream *TokenStream, bp int) (Node, error) {
	before := tokenStream.Current
	tokenStream.Advance()
	end := map[string]string{"[": "]", "{": "}", "(": ")"}[before.Type]
	children := []Node{}
	for {
		if tokenStream.Current.Type == end {
			break
		}
		child, err := Parse(tokenStream, lowPrec)
		if err != nil {
			return Node{}, err
		}
		children = append(children, child)
		if tokenStream.Current.Type != end {
			err := eat(tokenStream, ",")
			if err != nil {
				return Node{}, err
			}
		}
	}
	err := eat(tokenStream, end)
	if err != nil {
		return Node{}, err
	}
	return Node{before, children, false}, nil
}

// `foo ${a} ${[1, 2]} bar` becomes (` `foo ${ a } ${ ([1 2) } bar`)
// Templates are a bit weird in that Token("`foo ${") appears twice -
// as the operator and as a piece of template data.
func prefixVariadicTemplate(tokenStream *TokenStream, bp int) (Node, error) {
	before := tokenStream.Current
	tokenStream.Advance()

	first := before
	first.Type = template
	children := []Node{Node{first, []Node{}, false}}
	if !strings.HasSuffix(before.Value, "`") {
		for {
			if strings.HasSuffix(tokenStream.Current.Value, "`") {
				break
			}
			nextChild, err := Parse(tokenStream, bp)
			if err != nil {
				return Node{}, err
			}
			children = append(children, nextChild)
		}
		nextChild, err := Parse(tokenStream, bp)
		if err != nil {
			return Node{}, err
		}
		children = append(children, nextChild)
	}
	return Node{before, children, false}, nil
}

func raiseUnexpectedError(tokenStream *TokenStream, _ int) (Node, error) {
	return Node{}, ParseError{"unexpected token", tokenStream.Current}
}
func raiseUnexpectedErrorInfix(tokenStream *TokenStream, _ int, _ Node) (Node, error) {
	return Node{}, ParseError{"unexpected token", tokenStream.Current}
}
func raisePrefixError(tokenStream *TokenStream, _ int) (Node, error) {
	if tokenStream.Current.Type == eof {
		return Node{}, ParseError{"unexpected end of input", tokenStream.Current}
	}
	return Node{}, ParseError{"can't be used in prefix position", tokenStream.Current}
}
func raiseInfixError(tokenStream *TokenStream, _ int, _ Node) (Node, error) {
	return Node{}, ParseError{"can't be used in infix position", tokenStream.Current}
}

// populate infixRightAssoc, prefix, infix
type tablePrefix struct {
	Precedence int
	TokenTypes []string
	F          func(*TokenStream, int) (Node, error)
}
type tableInfix struct {
	Precedence int
	TokenTypes []string
	F          func(*TokenStream, int, Node) (Node, error)
}

var rulesPrefix = []tablePrefix{
	{-1, []string{"=", "=>", ")", "}", "]", ":", eof}, raisePrefixError},
	{-1, append(atoms, name), prefixAtom},
	{3, []string{"...", "import", "const", "export", "default"}, prefixUnary},
	{9, []string{"`"}, prefixVariadicTemplate},
	{20, []string{"[", "{", "("}, prefixVariadic},
}
var rulesInfix = []tableInfix{
	{lowPrec, []string{","}, raiseInfixError},
	{colonPrec, []string{":"}, infixBinary},
	{9, []string{"from", "="}, infixBinary},
	{10, []string{"=>"}, infixBinary},
	{11, []string{"==="}, infixBinary},
	{11, []string{"?"}, infixTernary},
	{20, []string{".", "("}, infixBinary},
}

func init() {
	infixRightAssoc["?"] = true
	for _, rule := range rulesPrefix {
		for _, tokenType := range rule.TokenTypes {
			prefix[tokenType] = rulePrefix{rule.F, rule.Precedence}
		}
	}
	for _, rule := range rulesInfix {
		for _, tokenType := range rule.TokenTypes {
			infix[tokenType] = ruleInfix{rule.F, rule.Precedence}
		}
	}
	for tokenType, _ := range infix {
		_, ruleIsAlreadyInPrefix := prefix[tokenType]
		if !ruleIsAlreadyInPrefix {
			prefix[tokenType] = rulePrefix{raisePrefixError, 0}
		}
	}
	for tokenType, _ := range prefix {
		_, ruleIsAlreadyInInfix := infix[tokenType]
		if !ruleIsAlreadyInInfix {
			infix[tokenType] = ruleInfix{raiseInfixError, 0}
		}
	}
}

type TypeMap map[string]string

func union(a TypeMap, b TypeMap) TypeMap {
	out := TypeMap{}
	for k, v := range a {
		out[k] = v
	}
	for k, v := range b {
		out[k] = v
	}
	return out
}
func identityMap(a []string) TypeMap {
	out := TypeMap{}
	for _, v := range a {
		out[v] = v
	}
	return out
}

var value = identityMap(append([]string{"(", "===", ".", "=>", "?", "[", "`", "{", apply}, atoms...))
var valueNoBrace = identityMap(append([]string{"(", "===", ".", "=>", "?", "[", "`", apply}, atoms...))
var childrenTypes = map[string][]TypeMap{
	name:     {},
	literal:  {},
	number:   {},
	str:      {},
	template: {},
	dName:    {},
	// unary
	"statement": {union(identityMap([]string{"const", "import", "export"}), value)},
	"const":     {identityMap([]string{"="})},
	"import":    {identityMap([]string{"from"})},
	"export":    {identityMap([]string{"default", "const"})},
	"default":   {value},
	"...":       {value},
	"(":         {value},
	// binary
	"=":    {{name: dName}, value},
	"===":  {value, value},
	".":    {valueNoBrace, {name: dName}},
	"from": {{"{": dBrace, name: dName}, {str: str}},
	":":    {{name: dName, str: str}, value},
	apply:  {value, {many: many}},
	"=>":   {{many: dMany}, valueNoBrace},
	// ternary
	"?": {value, value, value},
	// variadic
	"[":    {union(value, TypeMap{"...": "..."}), nil},
	"{":    {{":": ":", "...": "..."}, nil},
	"`":    {value, nil},
	many:   {value, nil},
	dBrack: {{name: dName}, nil},
	dBrace: {{name: dName}, nil},
	dMany:  {{name: dName, "[": dBrack}, nil},
}

func convertChildren(node Node) (Node, error) {
	ts, ok := childrenTypes[node.Token.Type]
	if !ok {
		panic(ok)
	}
	if len(ts) > 0 && ts[len(ts)-1] == nil {
		first := ts[0]
		ts = []TypeMap{}
		for _, _ = range node.Children {
			ts = append(ts, first)
		}
	}
	if len(node.Children) != len(ts) {
		return Node{}, ParseError{"operator has wrong number of arguments", node.Token}
	}
	for i, child := range node.Children {
		types := ts[i]
		typeKeys := []string{}
		for k, _ := range types {
			typeKeys = append(typeKeys, k)
		}
		if !containsString(typeKeys, child.Token.Type) {
			return Node{}, ParseError{
				fmt.Sprintf("token is not of type: %s", strings.Join(typeKeys, " ")),
				child.Token,
			}
		}
		child.Token.Type, _ = types[child.Token.Type]
		childOut, err := convertChildren(child)
		if err != nil {
			return Node{}, err
		}
		node.Children[i] = childOut
	}
	return node, nil
}

type ParseError struct {
	Message string
	Token   Token
}

func (e ParseError) Error() string {
	var source string
	var filepath string

	if strings.HasPrefix(*e.Token.Filepath, "memory://") {
		source = globalSourceMap[*e.Token.Filepath]
		filepath = "line"
	} else {
		dat, err := ioutil.ReadFile(*e.Token.Filepath)
		if err != nil {
			panic(err)
		}
		source = string(dat)
		filepath = *e.Token.Filepath
	}
	line := strings.Split(source+" ", "\n")[e.Token.Lineno-1]
	line = strings.TrimRight(line, whitespace)

	return fmt.Sprintf(
		"<ParserError %s:%d>\n"+
			"%s\n"+
			"%s\n"+
			"%s^",
		filepath, e.Token.Lineno, e.Message, line, strings.Repeat("_", e.Token.Linepos),
	)
}

func maxLineno(node Node, maxSoFar int) int {
	if node.Token.Lineno > maxSoFar {
		maxSoFar = node.Token.Lineno
	}
	for _, c := range node.Children {
		childMax := maxLineno(c, maxSoFar)
		if childMax > maxSoFar {
			maxSoFar = childMax
		}
	}
	return maxSoFar
}
