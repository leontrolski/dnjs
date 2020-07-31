import m from "mithril"

import { page } from "./basePage.dn.js"

const commentList = (comments) => m("ul",
    comments.map((comment, i) => m("li", `Comment ${i} says: ${comment.text}`))
)

export default (comments) => page(commentList(comments))
