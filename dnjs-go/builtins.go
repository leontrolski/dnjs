package main

import (
	"fmt"
	"regexp"
	"strings"
)

func truthy(value Value) bool {
	switch typed := value.(type) {
	case int64:
		return typed != int64(0)
	case float64:
		return typed != float64(0)
	case string:
		return typed != ""
	case bool:
		return typed
	}
	return value != nil
}

// dot builtin methods

func dotMap(l []Value) func(Node, ...Value) (Value, error) {
	return func(node Node, values ...Value) (Value, error) {
		f_, err := getUnary(values, false)
		if err != nil {
			return nil, ParseError{err.Error(), node.Token}
		}
		f, ok := f_.(Function)
		if !ok {
			return nil, ParseError{"attempting to call non-function", node.Token}
		}
		out := []Value{}
		for i, v := range l {
			n, err := f.Call(node, []Value{v, int64(i)}...)
			if err != nil {
				return nil, err
			}
			out = append(out, n)
		}
		return out, nil
	}
}

func dotFilter(l []Value) func(Node, ...Value) (Value, error) {
	return func(node Node, values ...Value) (Value, error) {
		f_, err := getUnary(values, false)
		if err != nil {
			return nil, ParseError{err.Error(), node.Token}
		}
		f, ok := f_.(Function)
		if !ok {
			return nil, ParseError{"attempting to call non-function", node.Token}
		}
		out := []Value{}
		for i, v := range l {
			n, err := f.Call(node, []Value{v, int64(i)}...)
			if err != nil {
				return nil, err
			}
			if truthy(n) {
				out = append(out, v)
			}
		}
		return out, nil
	}
}

func dotReduce(l []Value) func(Node, ...Value) (Value, error) {
	return func(node Node, values ...Value) (Value, error) {
		f_, initializer, err := getBinary(values, false)
		if err != nil {
			return nil, ParseError{err.Error(), node.Token}
		}
		f, ok := f_.(Function)
		if !ok {
			return nil, ParseError{"attempting to call non-function", node.Token}
		}
		for _, v := range l {
			initializer, err = f.Call(node, []Value{initializer, v}...)
			if err != nil {
				return nil, err
			}
		}
		return initializer, nil
	}
}

func dotContains(l []Value) func(Node, ...Value) (Value, error) {
	return func(node Node, values ...Value) (Value, error) {
		value, err := getUnary(values, false)
		if err != nil {
			return nil, ParseError{err.Error(), node.Token}
		}
		for _, v := range l {
			if v == value {
				return true, nil
			}
		}
		return false, nil
	}
}

// other builtins

var Object = map[string]Value{
	"entries": BuiltinFunction{"Object.entries", func(node Node, values ...Value) (Value, error) {
		value, err := getUnary(values, false)
		if err != nil {
			return nil, ParseError{err.Error(), node.Token}
		}
		o, ok := value.(map[string]Value)
		if !ok {
			return nil, ParseError{"can only get entries of {", node.Children[1].Token}
		}
		out := []Value{}
		for k, v := range o {
			out = append(out, []Value{k, v})
		}
		return out, nil
	}},
	"fromEntries": BuiltinFunction{"Object.fromEntries", func(node Node, values ...Value) (Value, error) {
		value, err := getUnary(values, false)
		if err != nil {
			return nil, ParseError{err.Error(), node.Token}
		}
		l, ok := value.([]Value)
		if !ok {
			return nil, ParseError{"can only get entries of [", node.Children[1].Token}
		}
		out := map[string]Value{}
		for _, v := range l {
			pair, ok := v.([]Value)
			if !ok || len(pair) != 2 {
				return nil, ParseError{"must be all (string, Value) pairs", node.Children[1].Token}
			}
			k, ok := pair[0].(string)
			if !ok {
				return nil, ParseError{"must be all (string, Value) pairs", node.Children[1].Token}
			}
			out[k] = pair[1]
		}
		return out, nil
	}},
}

func m(node Node, values ...Value) (Value, error) {
	out := map[string]Value{"tag": "div", "children": []Value{}}
	attrs := map[string]Value{"className": ""}

	if len(values) < 1 {
		return nil, ParseError{"m(...) must be called with more than one argument", node.Token}
	}
	first := values[0]
	properties, ok := first.(string)
	if !ok {
		return nil, ParseError{"first argument to m(...) must be a string", node.Children[1].Children[0].Token}
	}
	re := regexp.MustCompile(`(^|\.|#)([\w\d\-_]+)`)
	matches := re.FindAllStringSubmatch(properties, -1)
	if matches != nil {
		for _, match := range matches {
			type_ := match[1]
			p := match[2]
			switch type_ {
			case "":
				out["tag"] = p
			case "#":
				attrs["id"] = p
			case ".":
				className := attrs["className"].(string) + " " + p
				attrs["className"] = strings.TrimSpace(className)
			}

		}
	}
	if len(values) == 1 {
		out["attrs"] = attrs
		return out, nil
	}
	args := values[1:]
	tail := args
	if len(args) > 0 && !isRenderable(args[0]) {
		additionalAttrs, ok := args[0].(map[string]Value)
		if !ok {
			return nil, ParseError{"attributes must be a map of string to value", node.Children[1].Children[1].Token}
		}
		for k, v := range additionalAttrs {
			attrs[k] = v
		}
		if len(args) > 1 {
			tail = args[1:]
		} else {
			tail = []Value{}
		}
	}
	_, ok = attrs["class"]
	if ok {
		classList, ok := attrs["class"].([]Value)
		if !ok {
			return nil, ParseError{"class attribute must be an array of strings", node.Children[1].Children[1].Token}
		}
		delete(attrs, "class")
		for _, c := range classList {
			cString, ok := c.(string)
			if !ok {
				return nil, ParseError{"class attribute must be an array of strings", node.Children[1].Children[1].Token}
			}
			className := attrs["className"].(string) + " " + cString
			attrs["className"] = strings.TrimSpace(className)
		}
	}
	var addChildren func(v Value) error
	addChildren = func(v Value) error {
		if !isRenderable(v) {
			return ParseError{"one f the arguments to m(...) is not renderable", node.Token}
		}
		if v == nil {
			return nil
		}
		switch typed := v.(type) {
		case []Value:
			for _, v := range typed {
				err := addChildren(v)
				if err != nil {
					return err
				}
			}
		default:
			switch v.(type) {
			case int64, float64:
				v = fmt.Sprint(v)
			}
			children := append(out["children"].([]Value), v)
			out["children"] = children
		}
		return nil
	}
	err := addChildren(tail)
	if err != nil {
		return nil, err
	}
	out["attrs"] = attrs
	return out, nil
}

type TrustedHtml struct {
	Html string
}

func dotTrust(node Node, values ...Value) (Value, error) {
	value, err := getUnary(values, false)
	if err != nil {
		return nil, ParseError{err.Error(), node.Token}
	}
	switch typed := value.(type) {
	case string:
		return TrustedHtml{typed}, nil
	default:
		return nil, ParseError{"can only m.trust(...) string values", node.Token}
	}
}

func isVnode(dom Value) bool {
	matching := false
	switch typed := dom.(type) {
	case map[string]Value:
		matching = true
		_, ok := typed["tag"]
		matching = matching && ok
		_, ok = typed["attrs"]
		matching = matching && ok
		_, ok = typed["children"]
		matching = matching && ok
	}
	return matching
}

func isRenderable(dom Value) bool {
	if dom == nil {
		return true
	}
	switch dom.(type) {
	case int64, float64, string, TrustedHtml, []Value:
		return true
	}
	if isVnode(dom) {
		return true
	}
	return false
}

// dedent, lovingly copy-pasta-ed from https://github.com/lithammer/dedent/blob/master/dedent.go

var (
	whitespaceOnly    = regexp.MustCompile("(?m)^[ \t]+$")
	leadingWhitespace = regexp.MustCompile("(?m)(^[ \t]*)(?:[^ \t\n])")
)

func dedent(node Node, values ...Value) (Value, error) {
	value, err := getUnary(values, false)
	if err != nil {
		return nil, ParseError{err.Error(), node.Token}
	}
	text, ok := value.(string)
	if !ok {
		return nil, ParseError{"can only call with a string argument", node.Token}
	}

	var margin string

	text = whitespaceOnly.ReplaceAllString(text, "")
	indents := leadingWhitespace.FindAllStringSubmatch(text, -1)

	for i, indent := range indents {
		if i == 0 {
			margin = indent[1]
		} else if strings.HasPrefix(indent[1], margin) {
			continue
		} else if strings.HasPrefix(margin, indent[1]) {
			margin = indent[1]
		} else {
			margin = ""
			break
		}
	}

	if margin != "" {
		text = regexp.MustCompile("(?m)^"+margin).ReplaceAllString(text, "")
	}
	return strings.TrimSpace(text), nil
}
