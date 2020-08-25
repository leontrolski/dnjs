import m from "mithril"

export const page = (content) => m("html",
    m("head",
        m("script", {src: "someScript.js"})
    ),
    m("body", content),
)
