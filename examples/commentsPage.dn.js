import m from "mithril"

import { page } from "./basePage.dn.js"

const commentList = (comments) => m("ul",
    comments.map((v, i) => m("li", `Says: ${v.text}`))
)

export default (comments) => (page)((commentList)(comments))
