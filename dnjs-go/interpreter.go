package main

import (
	"fmt"
	"math"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
)

var missing = "<missing>"
var undefined = "<undefined>" // this should be some singleton

// Value should really be
//  int64
//  | float64
//  | string
//  | bool
//  | nil
//  | undefined
//  | map[string]Value
//  | []Value
//  | Function
//  | Unary
//  | Binary
type Value interface{}
type Scope map[string]Value
type Handler func(Scope, Node, ...Value) (Value, error)

type Module struct {
	Filepath      string
	Scope         Scope
	Exports       map[string]Value
	DefaultExport Value
	Value         Value
}

type Function interface {
	Call(node Node, args ...Value) (Value, error)
}
type DnjsFunction struct {
	Scope    Scope
	Node     Node
	ArgNames []Value // [](string|ArgNames)
	OutNode  Node
}
type BuiltinFunction struct {
	Name string
	F    func(node Node, args ...Value) (Value, error)
}

var handlers = map[string]Handler{}

func init() {
	handlers = map[string]Handler{
		// atoms
		name:     nameHandler,
		dName:    dNameHandler,
		literal:  literalHandler,
		number:   numberHandler,
		str:      strHandler,
		template: strHandler,

		// unary
		"const":   unaryHandler,
		"(":       identityHandler,
		"import":  unaryHandler,
		"export":  unaryHandler,
		"default": unaryHandler,
		"...":     unaryHandler,

		// binary
		"=":    binaryHandler,
		"===":  eqHandler,
		".":    dotHandler,
		"from": binaryHandler,
		":":    colonHandler,
		apply:  applyHandler,

		// ternary
		"?": ternaryHandler,

		// variadic
		"[":    arrayHandler,
		"{":    objectHandler,
		"`":    backtickHandler,
		many:   genericArrayHandler,
		dBrack: genericArrayHandler,
		dBrace: genericArrayHandler,
		dMany:  genericArrayHandler,
		"=>":   funcHandler,
	}
}

func interpretNode(scope Scope, node Node) (Value, error) {
	if node.IsQuoted {
		return node, nil
	}
	args := []Value{}
	for _, c := range node.Children {
		interpretedChild, err := interpretNode(scope, c)
		if err != nil {
			return Node{}, err
		}
		args = append(args, interpretedChild)
	}
	handler, ok := handlers[node.Token.Type]
	if !ok {
		panic(fmt.Sprintf("missing handler for %s", node.Token.Type))
	}
	value, err := handler(scope, node, args...)
	return value, err
}

func interpret(tokenStream *TokenStream) (Module, error) {
	scope := map[string]Value{
		"Object": Object,
		"m":      BuiltinFunction{"m", m},
		"dedent": BuiltinFunction{"dedent", dedent},
	}
	module := Module{
		Filepath:      tokenStream.Filepath,
		Scope:         Scope{},
		Exports:       map[string]Value{},
		DefaultExport: missing,
		Value:         missing,
	}
	statementNodes, err := ParseStatements(tokenStream)
	if err != nil {
		return Module{}, err
	}
	for _, statementNode := range statementNodes {
		statement, err := interpretNode(scope, statementNode)
		if err != nil {
			return Module{}, err
		}

		statementType := reflect.TypeOf(statement)
		if statementType == reflect.TypeOf(Unary{}) {
			op := statement.(Unary)
			if op.Node.Token.Type == "const" {
				assignment := op.Arg.(Binary)
				name := assignment.Left.(string)
				value := assignment.Right
				scope[name] = value
			} else if op.Node.Token.Type == "import" {
				from := op.Arg.(Binary)
				names := from.Left
				fromPath := from.Right.(string)
				if ([]rune(fromPath))[0] != '.' {
					continue
				}
				if !strings.HasSuffix(fromPath, ".dn.js") {
					return Module{}, ParseError{"can only import files ending .dn.js", op.Node.Token}
				}
				fromPath = filepath.Join(filepath.Dir(module.Filepath), fromPath)
				importTokenStream, err := TokenStreamFromFilepath(fromPath)
				if err != nil {
					return Module{}, err
				}
				module, err := interpret(&importTokenStream)
				if err != nil {
					return Module{}, err
				}
				importedModule := module

				if reflect.TypeOf(names).Kind() == reflect.String {
					if importedModule.DefaultExport == missing {
						return Module{}, ParseError{"missing export default", op.Node.Token}
					}
					scope[names.(string)] = importedModule.DefaultExport
				} else {
					for _, name := range names.([]Value) {
						scope[name.(string)] = importedModule.Exports[name.(string)]
					}
				}
			} else if op.Node.Token.Type == "export" {
				constOrDefault := op.Arg.(Unary)
				if constOrDefault.Node.Token.Type == "const" {
					assignment := constOrDefault.Arg.(Binary)
					name := assignment.Left.(string)
					value := assignment.Right
					scope[name] = value
					module.Exports[name] = value
				} else { // constOrDefault.Node.Token.Type == "default"
					module.DefaultExport = constOrDefault.Arg
				}
			} else {
				panic("unknown token type")
			}
		} else {
			module.Value = statement
		}
	}
	module.Scope = scope
	return module, nil
}

// handlers

func nameHandler(scope Scope, node Node, _ ...Value) (Value, error) {
	out, ok := scope[node.Token.Value]
	if !ok {
		return nil, ParseError{
			fmt.Sprintf("variable %s is not in scope", node.Token.Value),
			node.Token,
		}
	}
	return out, nil
}

func dNameHandler(_ Scope, node Node, _ ...Value) (Value, error) {
	return node.Token.Value, nil
}

func literalHandler(_ Scope, node Node, _ ...Value) (Value, error) {
	return map[string]Value{"null": nil, "true": true, "false": false}[node.Token.Value], nil
}

func numberHandler(_ Scope, node Node, _ ...Value) (Value, error) {
	if strings.Contains(node.Token.Value, ".") {
		n, err := strconv.ParseFloat(node.Token.Value, 64)
		if err != nil {
			return nil, ParseError{err.Error(), node.Token}
		}
		return n, nil
	}
	n, err := strconv.ParseInt(node.Token.Value, 10, 64)
	if err != nil {
		return nil, ParseError{err.Error(), node.Token}
	}
	return n, nil
}

func strHandler(_ Scope, node Node, _ ...Value) (Value, error) {
	end := len([]rune(node.Token.Value)) - 1
	if strings.HasSuffix(node.Token.Value, "${") {
		end = end - 1
	}
	return string([]rune(node.Token.Value)[1:end]), nil
}

type Unary struct {
	Node Node
	Arg  Value
}
type Binary struct {
	Node  Node
	Left  Value
	Right Value
}

func unaryHandler(_ Scope, node Node, values ...Value) (Value, error) {
	arg, _ := getUnary(values, true)
	return Unary{node, arg}, nil
}

func binaryHandler(_ Scope, node Node, values ...Value) (Value, error) {
	left, right, _ := getBinary(values, true)
	return Binary{node, left, right}, nil
}

func identityHandler(_ Scope, _ Node, values ...Value) (Value, error) {
	arg, _ := getUnary(values, true)
	return arg, nil
}

func eqHandler(_ Scope, node Node, values ...Value) (Value, error) {
	left, right, _ := getBinary(values, true)
	leftType := reflect.TypeOf(left)
	rightType := reflect.TypeOf(right)
	if leftType != rightType {
		return false, nil
	}
	if leftType.Kind() == reflect.Float64 && rightType.Kind() == reflect.Float64 {
		return math.Abs(left.(float64)-right.(float64)) <= 1e-9, nil
	}
	return left == right, nil
}

func isArray(value Value) bool {
	valueKind := reflect.TypeOf(value).Kind()
	return valueKind == reflect.Slice || valueKind == reflect.Array
}

func dotHandler(_ Scope, node Node, values ...Value) (Value, error) {
	value, name, _ := getBinary(values, true)
	if value == undefined {
		return nil, ParseError{fmt.Sprintf("cannot get .%s, value is undefined", name), node.Token}
	}
	if isArray(value) {
		l := value.([]Value)
		switch name {
		case "length":
			return int64(len(l)), nil
		case "map":
			return BuiltinFunction{"map", dotMap(l)}, nil
		case "filter":
			return BuiltinFunction{"filter", dotFilter(l)}, nil
		case "reduce":
			return BuiltinFunction{"reduce", dotReduce(l)}, nil
		case "includes":
			return BuiltinFunction{"includes", dotContains(l)}, nil
		}
	}

	if reflect.TypeOf(value) == reflect.TypeOf(BuiltinFunction{}) && value.(BuiltinFunction).Name == "m" {
		if name == "trust" {
			return BuiltinFunction{"m.trust", dotTrust}, nil
		}
	}

	if reflect.TypeOf(value).Kind() != reflect.Map {
		return undefined, nil
	}

	out, ok := value.(map[string]Value)[name.(string)]
	if !ok {
		return undefined, nil
	}
	return out, nil
}

func colonHandler(_ Scope, _ Node, values ...Value) (Value, error) {
	left, right, _ := getBinary(values, true)
	return []Value{left, right}, nil
}

func applyHandler(_ Scope, node Node, values ...Value) (Value, error) {
	left, right, _ := getBinary(values, true)
	f, ok := left.(Function)
	if !ok {
		return nil, ParseError{"attempting to call non-function", node.Token}
	}
	out, err := f.Call(node, right.([]Value)...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func ternaryHandler(scope Scope, _ Node, values ...Value) (Value, error) {
	predicate, ifTrue, ifFalse, _ := getTernary(values, true)
	if !reflect.ValueOf(predicate).IsZero() {
		ifTrueNode := ifTrue.(Node)
		ifTrueNode.IsQuoted = false
		return interpretNode(scope, ifTrueNode)
	}
	ifFalseNode := ifFalse.(Node)
	ifFalseNode.IsQuoted = false
	return interpretNode(scope, ifFalseNode)
}

func objectHandler(_ Scope, _ Node, values ...Value) (Value, error) {
	out := map[string]Value{}
	for _, value := range values {
		if reflect.TypeOf(value) == reflect.TypeOf(Unary{}) {
			ellipsis := value.(Unary).Arg
			if reflect.TypeOf(ellipsis).Kind() != reflect.Map {
				return nil, ParseError{"must be of type: {", value.(Unary).Node.Children[0].Token}
			}
			for k, v := range ellipsis.(map[string]Value) {
				out[k] = v
			}
		} else {
			k, v, _ := getBinary(value.([]Value), true)
			out[k.(string)] = v
		}
	}
	return out, nil
}

func arrayHandler(_ Scope, _ Node, values ...Value) (Value, error) {
	out := []Value{}
	for _, value := range values {
		if reflect.TypeOf(value) == reflect.TypeOf(Unary{}) {
			ellipsis := value.(Unary).Arg
			if !isArray(ellipsis) {
				return nil, ParseError{"must be of type: [", value.(Unary).Node.Children[0].Token}
			}
			for _, v := range ellipsis.([]Value) {
				out = append(out, v)
			}
		} else {
			out = append(out, value)
		}
	}
	return out, nil
}

func backtickHandler(_ Scope, _ Node, values ...Value) (Value, error) {
	out := ""
	for _, value := range values {
		out = out + fmt.Sprint(value)
	}
	return out, nil
}

func genericArrayHandler(_ Scope, _ Node, values ...Value) (Value, error) {
	return values, nil
}

func funcHandler(scope Scope, node Node, values ...Value) (Value, error) {
	argNames, outNode, _ := getBinary(values, true)
	return DnjsFunction{scope, node, argNames.([]Value), outNode.(Node)}, nil
}

// Call methods

func (f DnjsFunction) Call(node Node, args ...Value) (Value, error) {
	newScope := map[string]Value{}
	for k, v := range f.Scope {
		newScope[k] = v
	}
	for i, argName := range f.ArgNames {
		if isArray(argName) {
			if !isArray(args[i]) {
				return nil, ParseError{
					"cannot unpack argument",
					node.Children[1].Children[i].Token,
				}
			}
			for j, nestedArgName := range argName.([]Value) {
				if i < len(args) && j < len(args[i].([]Value)) {
					newScope[nestedArgName.(string)] = args[i].([]Value)[j]
				}
			}
		} else if i < len(args) {
			newScope[argName.(string)] = args[i]
		}
	}
	outNode := f.OutNode
	outNode.IsQuoted = false
	return interpretNode(newScope, outNode)
}

func (f DnjsFunction) String() string {
	return "<function: " + f.Node.String() + ">"
}

func (f BuiltinFunction) Call(node Node, args ...Value) (Value, error) {
	return f.F(node, args...)
}

func (f BuiltinFunction) String() string {
	return "<builtin: " + f.Name + ">"
}

// arg transformers

func getUnary(values []Value, doPanic bool) (Value, error) {
	if len(values) != 1 {
		if doPanic {
			panic("expected 1 argument")
		}
		return nil, fmt.Errorf("expected 1 argument")
	}
	return values[0], nil
}
func getBinary(values []Value, doPanic bool) (Value, Value, error) {
	if len(values) != 2 {
		if doPanic {
			panic("expected 2 arguments")
		}
		return nil, nil, fmt.Errorf("expected 2 arguments")
	}
	return values[0], values[1], nil
}
func getTernary(values []Value, doPanic bool) (Value, Value, Value, error) {
	if len(values) != 3 {
		if doPanic {
			panic("expected 3 arguments")
		}
		return nil, nil, nil, fmt.Errorf("expected 3 arguments")
	}
	return values[0], values[1], values[2], nil
}