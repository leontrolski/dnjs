package main

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

var expectedHtml = `<div id="account-filters">
    <h3>
        <button class="fold-button" title="expand">
            ⇕
        </button>
        Filters  🔍
    </h3>
    <div class="to-fold hidden">

    </div>
    <h3>
        <a href="#foo">
            You &amp; I
        </a>

    </h3>
    <form class="members_by_member_ids" id="my-form">
        <input class="my-input" name="member_ids" placeholder="hello: M-00-0000-0001">
        no escape: &
    </form>

</div>
`

func TestRenderHtml(t *testing.T) {
	tokenStream, _ := TokenStreamFromFilepath("../test/data/account.dn.js")
	module, err := interpret(&tokenStream)
	assert.Nil(t, err)

	input := map[string]Value{
		"route_args": []string{},
		"members":    []Value{map[string]Value{"name": "Oli"}},
		"onClickF":   nil,
	}

	f := module.DefaultExport.(Function)
	data, err := f.Call(Node{}, input)
	assert.Nil(t, err)
	htmlString, err := ToHtml(data)
	assert.Nil(t, err)
	assert.Equal(t, htmlString, expectedHtml)
}
