package main

import (
	"fmt"
	"sort"
)

func assertMap(value Value) ([]string, map[string]Value, error) {
	switch typed := value.(type) {
	case map[string]Value:
		// sort keys
		keys := []string{}
		for k, _ := range typed {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		return keys, typed, nil
	default:
		return nil, nil, fmt.Errorf("value cannot be converted to css: " + fmt.Sprint(value))
	}
}

func ToCss(value Value) (string, error) {
	keys, typed, err := assertMap(value)
	if err != nil {
		return "", err
	}
	out := ""
	for _, k := range keys {
		v := typed[k]
		attrs, typedV, err := assertMap(v)
		if err != nil {
			return "", err
		}
		cssValues := ""
		for _, attr := range attrs {
			cssValue := typedV[attr]
			cssValues += fmt.Sprintf("    %s: %s;", attr, cssValue)
		}
		out += fmt.Sprintf("%s {\n%s\n}\n", k, cssValues)
	}
	return out, nil
}
