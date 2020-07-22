import m from "mithril"

import { base, form } from "./base.dn.js"

// some comment
const hiddenClass = "hidden"  // some other comment

export default (ctx) => m("#account-filters",
    m("h3",
        m("button.fold-button", {"title": "expand", "onclick": ctx.onClickF}, "⇕"),
        "Filters  🔍"),
    m(".to-fold", {"class": [ctx.members.length === 1 ? hiddenClass : ""]}),
    m("h3", m("a", {"href": "#foo"}, "You & I")),
    (form)(ctx.route_args, "members_by_member_ids", {"member_ids": "M-00-0000-0001"})
)
