package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestRenderCss(t *testing.T) {
	tokenStream, _ := TokenStreamFromFilepath("../examples/css.dn.js")
	module, err := interpret(&tokenStream)
	assert.Nil(t, err)

	cssString, err := ToCss(module.DefaultExport)
	assert.Nil(t, err)

	expected := `.bold {
    font-weight: bold;
}
.red {
    color: red;
}
`
	assert.Equal(t, cssString, expected)
}
