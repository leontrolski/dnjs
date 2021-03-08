package main

import (
	"fmt"
	"html"
	"reflect"
	"sort"
	"strings"
)

var selfClosing = []string{
	"area",
	"base",
	"br",
	"col",
	"embed",
	"hr",
	"img",
	"input",
	"link",
	"meta",
	"param",
	"source",
	"track",
	"wbr",
}

func ToHtml(value Value) (string, error) {
	return toHtml(value, 0)
}

func toHtml(value Value, indent int) (string, error) {
	indentString := strings.Repeat("    ", indent)
	if !isRenderable(value) {
		return "", fmt.Errorf("value cannot be converted to html: " + fmt.Sprint(value))
	}
	if value == nil {
		return "", nil
	}
	if reflect.TypeOf(value) == reflect.TypeOf(TrustedHtml{}) {
		return indentString + value.(TrustedHtml).Html, nil
	}
	switch v := value.(type) {
	case string:
		return indentString + html.EscapeString(v), nil
	case int64:
		return indentString + fmt.Sprint(v), nil
	case float64:
		return indentString + fmt.Sprint(v), nil
	}
	// else is vnode
	vNode := value.(map[string]Value)
	_, hasTag := vNode["tag"]
	_, hasAttrs := vNode["attrs"]
	_, hasChildren := vNode["children"]
	if !hasTag || !hasAttrs || !hasChildren {
		return "", fmt.Errorf("value must have tag, attrs, children attributes")
	}

	tag, ok := vNode["tag"].(string)
	if !ok {
		return "", fmt.Errorf("tag must be a string")
	}
	attrs, ok := vNode["attrs"].(map[string]Value)
	if !ok {
		return "", fmt.Errorf("attributes must be a map of string to value")
	}
	children, ok := vNode["children"].([]Value)
	if !ok {
		return "", fmt.Errorf("children must be an array of values")
	}

	// sort keys first
	keys := []string{}
	for k, _ := range attrs {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	attrsStr := ""
	for _, k := range keys {
		v := attrs[k]
		if k == "className" {
			k = "class"
			if reflect.ValueOf(v).IsZero() {
				continue
			}
		}
		if v == nil || v == false {
			// pass
		} else if v == true {
			attrsStr += " " + html.EscapeString(k)
		} else {
			switch v_ := v.(type) {
			case string:
				attrsStr += " " + html.EscapeString(k) + "=\"" + html.EscapeString(v_) + "\""
			case int64:
				attrsStr += " " + html.EscapeString(k) + "=\"" + fmt.Sprint(v_) + "\""
			case float64:
				attrsStr += " " + html.EscapeString(k) + "=\"" + fmt.Sprint(v_) + "\""
			default:
				return "", fmt.Errorf("unable to render attribute type")
			}
		}
	}
	isSelfClosing := containsString(selfClosing, tag) && len(children) == 0
	htmlStr := indentString + "<" + html.EscapeString(tag) + attrsStr + ">\n"
	if !isSelfClosing {
		if containsString([]string{"pre", "code", "textarea"}, tag) {
			htmlStr = string(([]rune(htmlStr))[0 : len([]rune(htmlStr))-1]) // strip \n
			for _, c := range children {
				innerHtmlStr, err := toHtml(c, 0)
				if err != nil {
					return "", err
				}
				htmlStr += innerHtmlStr
			}
			htmlStr += "</" + html.EscapeString(tag) + ">\n"
		} else {
			for _, c := range children {
				innerHtmlStr, err := toHtml(c, indent+1)
				if err != nil {
					return "", err
				}
				htmlStr += innerHtmlStr
			}
			htmlStr += "\n" + indentString + "</" + html.EscapeString(tag) + ">\n"
		}
	}
	return htmlStr, nil
}
