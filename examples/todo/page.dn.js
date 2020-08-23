import { classes } from "./style.dn.js"

const title = [classes.bold, classes.red]

export default (pageData) => m("html",
    m("meta", {"name": "viewport", "content": "width=device-width", "initial-scale": "1.0"}),
    m("head",
        m("title", "TODO list"),
        m("link", {"href": "static/style.css", "rel": "stylesheet"}),
    ),
    m("body",
        m("", {"class": title}, "hello ", pageData.username),
    )
)
