import assert from 'assert'
import dedent from 'dedent'
import render from 'mithril-node-render'
import html from 'html'

import account from './data/account.dn.js'

const r = (vnode) => html.prettyPrint(render.sync(vnode));

describe('#indexOf()', () => {
    it('should render', () => {
        const expected = dedent`<div id="account-filters">
            <h3><button title="expand" class="fold-button">⇕</button>Filters  🔍</h3>
            <div class="to-fold hidden"></div>
            <h3><a href="#foo">You &amp; I</a></h3>
            <form id="my-form" class="members_by_member_ids">
                <input name="member_ids" placeholder="hello: M-00-0000-0001" class="my-input">no escape: &</form>
        </div>`
        const ctx = {
            route_args: [],
            members: [{name: "Oli"}],
        }
        const actual = r(account(ctx))
        assert.equal(actual, expected)
    })
})
