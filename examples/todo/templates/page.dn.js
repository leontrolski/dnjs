import { classes } from "../static/style.dn.js"

const title = [classes.bold, classes.red]

export default (pageData) => m("html",
    m("meta", {name: "viewport", content: "width=device-width", "initial-scale": "1.0"}),
    m("head",
        m("title", "TODO list"),
        m("link", {href: "static/style.css", rel: "stylesheet"}),
        m("script", {src: "https://unpkg.com/mithril@2.0.4/mithril.min.js"}),
        m("script", {src: "static/comments.js", type: "module"}),
    ),
    m("body",
        m("h1", {class: title}, "hello ", pageData.username),
        m("#todo-list", ""),
    )
)
