import { classes } from "../shared/style.dn.js"
import { TodoList } from "../shared/components.dn.js"

const title = [classes.bold, classes.red]

export default (data) => m("html",
    m("meta", {name: "viewport", content: "width=device-width", "initial-scale": "1.0"}),
    m("head",
        m("title", "TODO list"),
        m("link", {href: "static/style.css", rel: "stylesheet"}),
        data.type === "backend" ? m("script", {src: "static/backend.js", defer: true}) : null,
        data.type === "classic" ? m("script", {type: "module"}, m.trust("import m from 'https://unpkg.com/dnjs2dom@0.0.3/index.js'; window.m = m;")) : null,
        data.type === "classic" ? m("script", {src: "static/classic.js", defer: true, type: "module"}) : null,
        data.type === "declarative" ? m("script", {src: "https://unpkg.com/mithril@2.0.4/mithril.min.js"}) : null,
        data.type === "declarative" ? m("script", {src: "static/declarative.js", type: "module"}): null,
    ),
    m("body",
        m("h1", {class: title}, "Hello ", data.username),
        m("#todo-list",
            data.type === "backend" ? TodoList(data.state, data.actions) : null,
            data.type === "classic" ? TodoList(data.state, data.actions) : null,
        ),
    )
)
